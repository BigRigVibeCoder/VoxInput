"""src/errors.py — VoxInput error taxonomy per GOV-004.

Implements the ApplicationError hierarchy with structured ErrorContext
for the 13-category error taxonomy. All custom exceptions carry:
  - error_id (unique)
  - category (ErrorCategory enum)
  - operation (what was happening)
  - component (where it happened)
  - retryable flag

Usage:
    raise AudioIOError(
        "Microphone stream died",
        context=ErrorContext(
            operation="start_listening",
            component="audio",
        ),
        cause=original_exception,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4


# ── Error Categories (GOV-004 §2) ────────────────────────────────────────────

class ErrorCategory(Enum):
    """13-category error taxonomy per GOV-004 §2."""
    VALIDATION = auto()
    BUSINESS_LOGIC = auto()
    EXTERNAL_SERVICE = auto()
    DATABASE = auto()
    RESOURCE = auto()
    INFRASTRUCTURE = auto()
    CONFIGURATION = auto()
    NETWORK = auto()
    SECURITY = auto()
    HARDWARE = auto()
    FATAL = auto()
    TRANSIENT = auto()
    UNKNOWN = auto()


# ── Structured Error Context (GOV-004 §3.1) ──────────────────────────────────

@dataclass
class ErrorContext:
    """Structured context attached to every application error.

    Attributes:
        error_id: Unique identifier for this error instance.
        category: ErrorCategory from the GOV-004 taxonomy.
        operation: What operation was in progress when the error occurred.
        component: Which module/service raised the error.
        correlation_id: Request trace ID (if applicable).
        input_data: Sanitized inputs — NO secrets, passwords, or tokens.
        retryable: Whether the caller should attempt a retry.
    """
    error_id: str = field(default_factory=lambda: f"err-{uuid4().hex[:12]}")
    category: ErrorCategory = ErrorCategory.UNKNOWN
    operation: str | None = None
    component: str | None = None
    correlation_id: str | None = None
    input_data: dict[str, Any] | None = None
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for structured logging."""
        return {
            "error_id": self.error_id,
            "category": self.category.name,
            "operation": self.operation,
            "component": self.component,
            "correlation_id": self.correlation_id,
            "retryable": self.retryable,
        }


# ── Base ApplicationError (GOV-004 §3.1) ─────────────────────────────────────

class ApplicationError(Exception):
    """Base exception for all VoxInput application errors.

    Carries structured ErrorContext for forensic logging.
    Always chain with `raise ... from original` to preserve the cause.
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.context = context or ErrorContext()
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return f"[{self.context.category.name}:{self.context.error_id}] {super().__str__()}"


# ── Domain-Specific Subclasses (VoxInput) ─────────────────────────────────────

class AudioIOError(ApplicationError):
    """Audio stream or hardware failure (HARDWARE category).

    Examples: microphone disconnect, PyAudio stream crash, PortAudio error.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", None) or ErrorContext(
            category=ErrorCategory.HARDWARE,
            component="audio",
        )
        super().__init__(message, context=ctx, **kwargs)


class EngineCrashError(ApplicationError):
    """Speech engine failure — Vosk or Whisper (INFRASTRUCTURE category).

    Examples: model load failure, KaldiRecognizer abort, CUDA OOM.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", None) or ErrorContext(
            category=ErrorCategory.INFRASTRUCTURE,
            component="recognizer",
        )
        super().__init__(message, context=ctx, **kwargs)


class InjectionFallbackError(ApplicationError):
    """All injection backends failed (EXTERNAL_SERVICE category).

    Examples: ydotool + xdotool + pynput all unavailable/crashing.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", None) or ErrorContext(
            category=ErrorCategory.EXTERNAL_SERVICE,
            component="injection",
            retryable=True,
        )
        super().__init__(message, context=ctx, **kwargs)


class ConfigurationError(ApplicationError):
    """Configuration error — invalid settings, missing model path.

    Examples: corrupt settings.json, model directory missing.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", None) or ErrorContext(
            category=ErrorCategory.CONFIGURATION,
            component="config",
        )
        super().__init__(message, context=ctx, **kwargs)


class ResourceError(ApplicationError):
    """Missing resource — file not found, DB inaccessible.

    Examples: word database missing, seed data unavailable.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", None) or ErrorContext(
            category=ErrorCategory.RESOURCE,
            component="resource",
        )
        super().__init__(message, context=ctx, **kwargs)
