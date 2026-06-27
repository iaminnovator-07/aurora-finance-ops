"""FastAPI dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")
    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
