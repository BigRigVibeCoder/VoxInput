"""tests/unit/test_errors.py — Unit tests for src/errors.py (GOV-004 taxonomy).

Tests the ApplicationError hierarchy, ErrorContext, and structured payload.
"""
import pytest

from src.errors import (
    ApplicationError,
    AudioIOError,
    ConfigurationError,
    EngineCrashError,
    ErrorCategory,
    ErrorContext,
    InjectionFallbackError,
    ResourceError,
)


class TestErrorContext:
    """Verify ErrorContext defaults and serialization."""

    def test_default_fields(self):
        ctx = ErrorContext()
        assert ctx.error_id.startswith("err-")
        assert ctx.category == ErrorCategory.UNKNOWN
        assert ctx.retryable is False
        assert ctx.operation is None

    def test_to_dict(self):
        ctx = ErrorContext(
            category=ErrorCategory.HARDWARE,
            operation="start_listening",
            component="audio",
        )
        d = ctx.to_dict()
        assert d["category"] == "HARDWARE"
        assert d["operation"] == "start_listening"
        assert d["component"] == "audio"
        assert d["retryable"] is False

    def test_unique_error_ids(self):
        ids = {ErrorContext().error_id for _ in range(100)}
        assert len(ids) == 100  # all unique


class TestApplicationError:
    """Verify base ApplicationError behavior."""

    def test_message(self):
        e = ApplicationError("something broke")
        assert "something broke" in str(e)

    def test_default_context(self):
        e = ApplicationError("test")
        assert e.context.category == ErrorCategory.UNKNOWN

    def test_custom_context(self):
        ctx = ErrorContext(category=ErrorCategory.FATAL, component="core")
        e = ApplicationError("fatal", context=ctx)
        assert e.context.category == ErrorCategory.FATAL
        assert e.context.component == "core"

    def test_cause_chaining(self):
        original = ValueError("bad value")
        e = ApplicationError("wrapped", cause=original)
        assert e.__cause__ is original

    def test_str_includes_category_and_id(self):
        e = ApplicationError("test")
        s = str(e)
        assert "UNKNOWN" in s
        assert "err-" in s


class TestAudioIOError:
    """Verify AudioIOError defaults."""

    def test_defaults_to_hardware(self):
        e = AudioIOError("mic died")
        assert e.context.category == ErrorCategory.HARDWARE
        assert e.context.component == "audio"

    def test_is_application_error(self):
        assert isinstance(AudioIOError("x"), ApplicationError)


class TestEngineCrashError:
    """Verify EngineCrashError defaults."""

    def test_defaults_to_infrastructure(self):
        e = EngineCrashError("Vosk abort")
        assert e.context.category == ErrorCategory.INFRASTRUCTURE
        assert e.context.component == "recognizer"


class TestInjectionFallbackError:
    """Verify InjectionFallbackError defaults."""

    def test_defaults_to_external_service(self):
        e = InjectionFallbackError("all backends down")
        assert e.context.category == ErrorCategory.EXTERNAL_SERVICE
        assert e.context.retryable is True


class TestConfigurationError:
    """Verify ConfigurationError defaults."""

    def test_defaults_to_configuration(self):
        e = ConfigurationError("bad settings.json")
        assert e.context.category == ErrorCategory.CONFIGURATION


class TestResourceError:
    """Verify ResourceError defaults."""

    def test_defaults_to_resource(self):
        e = ResourceError("model file missing")
        assert e.context.category == ErrorCategory.RESOURCE


class TestErrorCategoryEnum:
    """Verify all 13 categories exist."""

    def test_all_13_categories(self):
        assert len(ErrorCategory) == 13
        names = {c.name for c in ErrorCategory}
        required = {
            "VALIDATION", "BUSINESS_LOGIC", "EXTERNAL_SERVICE", "DATABASE",
            "RESOURCE", "INFRASTRUCTURE", "CONFIGURATION", "NETWORK",
            "SECURITY", "HARDWARE", "FATAL", "TRANSIENT", "UNKNOWN",
        }
        assert names == required
