from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MessageSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationMessage:
    severity: MessageSeverity
    code: str
    message: str
    field: str | None = None

    @classmethod
    def info(cls, code: str, message: str, field: str | None = None) -> "ValidationMessage":
        return cls(MessageSeverity.INFO, code, message, field)

    @classmethod
    def warning(cls, code: str, message: str, field: str | None = None) -> "ValidationMessage":
        return cls(MessageSeverity.WARNING, code, message, field)

    @classmethod
    def error(cls, code: str, message: str, field: str | None = None) -> "ValidationMessage":
        return cls(MessageSeverity.ERROR, code, message, field)


@dataclass(frozen=True)
class ConflictMessage:
    severity: MessageSeverity
    code: str
    message: str
    field: str | None = None
    offer_sources: tuple[str, ...] = ()

