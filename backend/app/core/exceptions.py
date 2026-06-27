"""Application exception hierarchy."""

from typing import Any


class AuroraException(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "AURORA_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        reason: str | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.reason = reason or message
        super().__init__(message)


class NotFoundError(AuroraException):
    def __init__(self, resource: str, identifier: str | None = None):
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} '{identifier}' not found"
        super().__init__(msg, code="NOT_FOUND", status_code=404)


class UnauthorizedError(AuroraException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, code="UNAUTHORIZED", status_code=401)


class ForbiddenError(AuroraException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ValidationError(AuroraException):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)


class ProcessingError(AuroraException):
    def __init__(self, message: str, *, reason: str | None = None):
        super().__init__(message, code="PROCESSING_ERROR", status_code=500, reason=reason)
