"""tests/unit/test_logger.py — Unit tests for P7 enterprise logging (HM-IPV-005/003/018)."""
import logging
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, ".")


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path) -> Path:
    return tmp_path / "test_voxinput_logging.db"


@pytest.fixture
def fresh_logger(tmp_db, monkeypatch):
    """Initialise logging in isolation with a temp DB path."""
    monkeypatch.setenv("LOG_LEVEL", "TRACE")
    monkeypatch.setenv("LOG_DB_PATH", str(tmp_db))
    monkeypatch.setenv("LOG_CONSOLE", "false")  # suppress stdout noise in tests

    # Clear existing handlers to avoid pollution between tests
    root = logging.getLogger()
    root.handlers.clear()

    from src.logger import init_logging
    logger = init_logging("test_component")
    yield logger

    # Cleanup
    root.handlers.clear()


# ─── TRACE level ──────────────────────────────────────────────────────────────

class TestTraceLevelRegistration:

    def test_trace_level_value(self):
        from src.logger import TRACE
        assert TRACE == 5

    def test_trace_level_name(self):
        assert logging.getLevelName(5) == "TRACE"

    def test_trace_below_debug(self):
        from src.logger import TRACE
        assert TRACE < logging.DEBUG


class TestTraceCallable:

    def test_trace_method_on_logger(self, fresh_logger):
        log = logging.getLogger("trace_test")
        # Should not raise
        log.trace("test_trace_event", extra={"key": "val"})  # type: ignore[attr-defined]

    def test_trace_level_enabled(self, fresh_logger):
        log = logging.getLogger("trace_enabled_test")
        from src.logger import TRACE
        # When LOG_LEVEL=TRACE the logger should enable it
        assert log.isEnabledFor(TRACE)


# ─── SQLite DB creation ───────────────────────────────────────────────────────

class TestSQLiteSetup:

    def test_db_file_created(self, fresh_logger, tmp_db):
        time.sleep(0.15)  # allow flush thread
        assert tmp_db.exists(), f"DB not created at {tmp_db}"

    def test_system_logs_table_exists(self, fresh_logger, tmp_db):
        time.sleep(0.15)
        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'"
        )
        assert cursor.fetchone() is not None, "system_logs table not found"
        conn.close()

    def test_crash_artifacts_table_exists(self, fresh_logger, tmp_db):
        time.sleep(0.15)
        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='crash_artifacts'"
        )
        assert cursor.fetchone() is not None, "crash_artifacts table not found"
        conn.close()

    def test_wal_mode_active(self, fresh_logger, tmp_db):
        time.sleep(0.15)
        conn = sqlite3.connect(str(tmp_db))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal", f"Expected WAL, got: {mode}"

    def test_indexes_exist(self, fresh_logger, tmp_db):
        time.sleep(0.15)
        conn = sqlite3.connect(str(tmp_db))
        indexes = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()]
        conn.close()
        assert "idx_logs_time" in indexes
        assert "idx_logs_level" in indexes


# ─── SqliteHandler batching ───────────────────────────────────────────────────

class TestSqliteHandlerBatching:

    def test_records_written_to_db(self, fresh_logger, tmp_db):
        log = logging.getLogger("batch_test")
        for i in range(5):
            log.info("batch_event_%d", i)
        time.sleep(0.35)  # allow at least 2 flush cycles

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM system_logs").fetchone()[0]
        conn.close()
        assert count >= 5, f"Expected ≥5 rows, got {count}"

    def test_trace_records_in_db(self, fresh_logger, tmp_db):
        log = logging.getLogger("trace_db_test")
        log.trace("trace_record")  # type: ignore[attr-defined]
        time.sleep(0.35)

        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute(
            "SELECT level FROM system_logs WHERE level='TRACE' LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None, "No TRACE rows written to system_logs"

    def test_level_column_populated(self, fresh_logger, tmp_db):
        log = logging.getLogger("level_col_test")
        log.warning("level_test_warning")
        time.sleep(0.35)

        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute(
            "SELECT level FROM system_logs WHERE level='WARNING' LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None


# ─── Auto-trim ────────────────────────────────────────────────────────────────

class TestAutoTrim:

    def test_trim_runs_without_error(self, fresh_logger, tmp_db):
        """Trim should not raise even on empty DB."""
        from src.logger import get_sqlite_handler
        handler = get_sqlite_handler()
        assert handler is not None
        try:
            handler._trim()
        except Exception as e:
            pytest.fail(f"_trim() raised: {e}")

    def test_trim_removes_old_trace_rows(self, fresh_logger, tmp_db):
        """Insert a row with an ancient timestamp and verify trim removes it."""
        from src.logger import get_sqlite_handler
        handler = get_sqlite_handler()
        assert handler is not None

        # Insert an old TRACE row (2 days ago)
        old_ts = time.time() - (2 * 24 * 3600)
        handler._conn.execute(
            "INSERT INTO system_logs (timestamp, level, component, event) VALUES (?,?,?,?)",
            (old_ts, "TRACE", "test", "old_event")
        )
        handler._conn.commit()

        handler._trim()

        count = handler._conn.execute(
            "SELECT COUNT(*) FROM system_logs WHERE event='old_event'"
        ).fetchone()[0]
        assert count == 0, "Old TRACE row should have been trimmed"

    def test_trim_preserves_error_rows(self, fresh_logger, tmp_db):
        """ERROR rows should never be trimmed."""
        from src.logger import get_sqlite_handler
        handler = get_sqlite_handler()
        assert handler is not None

        old_ts = time.time() - (365 * 24 * 3600)  # 1 year ago
        handler._conn.execute(
            "INSERT INTO system_logs (timestamp, level, component, event) VALUES (?,?,?,?)",
            (old_ts, "ERROR", "test", "old_error_event")
        )
        handler._conn.commit()

        handler._trim()

        count = handler._conn.execute(
            "SELECT COUNT(*) FROM system_logs WHERE event='old_error_event'"
        ).fetchone()[0]
        assert count == 1, "ERROR rows must never be trimmed"


# ─── Exception hook ───────────────────────────────────────────────────────────

class TestExcepthook:

    def test_excepthook_installed(self, fresh_logger):
        assert sys.excepthook is not sys.__excepthook__, (
            "sys.excepthook was not replaced by init_logging()"
        )

    def test_crash_artifact_written(self, fresh_logger, tmp_db):
        from src.logger import get_sqlite_handler
        handler = get_sqlite_handler()
        assert handler is not None

        handler.write_crash_artifact(
            error_id="crash-test-001",
            message="test crash",
            stack_trace="Traceback: test",
            system_state={"python": "3.12", "test": True}
        )

        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute(
            "SELECT error_id, message FROM crash_artifacts WHERE error_id='crash-test-001'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "test crash"


# ─── .env loading ─────────────────────────────────────────────────────────────

class TestDotEnvLoading:

    def test_log_level_from_env_var(self, tmp_db, monkeypatch, tmp_path):
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        monkeypatch.setenv("LOG_DB_PATH", str(tmp_db))
        monkeypatch.setenv("LOG_CONSOLE", "false")

        root = logging.getLogger()
        root.handlers.clear()

        from src.logger import init_logging, TRACE
        init_logging("env_test")

        log = logging.getLogger("env_test_log")
        assert not log.isEnabledFor(TRACE), "TRACE should be disabled when LOG_LEVEL=INFO"
        root.handlers.clear()

    def test_load_dotenv_parses_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("LOG_LEVEL=WARNING\nLOG_CONSOLE=false\n")

        # Patch ROOT_DIR inside logger
        import src.logger as logger_mod
        monkeypatch.setattr(logger_mod, "ROOT_DIR", tmp_path)

        env = logger_mod._load_dotenv()
        assert env.get("LOG_LEVEL") == "WARNING"
        assert env.get("LOG_CONSOLE") == "false"
