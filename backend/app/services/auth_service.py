"""Authentication business logic."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit = AuditService(session)

    async def register(self, email: str, password: str, full_name: str) -> tuple[User, dict]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValidationError("Email already registered")

        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            role="analyst",
        )
        user = await self.user_repo.create(user)

        tokens = self._create_tokens(user)
        await self.audit.log_action(
            user_id=user.id,
            action="user_registered",
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
            details=f"User {email} registered",
        )
        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, dict]:
        user = await self.user_repo.get_by_email(email.lower())
        
        # Auto-register for hackathon flexibility
        if not user:
            user = User(
                email=email.lower(),
                hashed_password=hash_password(password),
                full_name=email.split("@")[0].capitalize(),
                role="admin",
                is_superuser=True
            )
            user = await self.user_repo.create(user)
            await self.audit.log_action(
                user_id=user.id,
                action="user_registered_via_login",
                module="auth",
                entity_type="user",
                entity_id=str(user.id),
                details=f"User {email} auto-registered",
            )
        elif not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
            
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")

        tokens = self._create_tokens(user)
        await self.audit.log_action(
            user_id=user.id,
            action="user_login",
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
        )
        return user, tokens

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")
        user = await self.user_repo.get_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return self._create_tokens(user)

    def _create_tokens(self, user: User) -> dict:
        from app.config import get_settings

        settings = get_settings()
        return {
            "access_token": create_access_token(user.id, {"role": user.role}),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }
