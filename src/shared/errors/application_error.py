from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence


class ApplicationError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        canonical_code: str = "INTERNAL_ERROR",
        retryable: bool = False,
        details: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.canonical_code = canonical_code
        self.retryable = retryable
        self.details = details or ()


class ValidationError(ApplicationError):
    def __init__(
        self,
        message: str,
        details: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            canonical_code="VALIDATION_FAILED",
            retryable=False,
            details=details,
        )


class NotFoundError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=404,
            canonical_code="RESOURCE_NOT_FOUND",
            retryable=False,
        )


class ConflictError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=409,
            canonical_code="CONFLICT",
            retryable=False,
        )
