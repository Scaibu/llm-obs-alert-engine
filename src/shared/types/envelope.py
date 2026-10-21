from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Mapping, Optional, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ApiErrorDetail:
    field: str
    issue: str
    rule: str
    rejected_value: Any = None


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    retryable: bool
    details: Optional[Sequence[ApiErrorDetail]] = None


@dataclass(frozen=True)
class ApiMeta:
    request_id: str
    correlation_id: str
    timestamp: str
    execution_time_ms: int
    api_version: str = "v1"


@dataclass(frozen=True)
class ApiResponse(Generic[T]):
    success: bool
    status_code: int
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: Optional[ApiMeta] = None
