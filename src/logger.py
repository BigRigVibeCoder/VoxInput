"""
src/logger.py — VoxInput Enterprise Logging
=============================================
Implements the "Flight Recorder" standard adapted from HM-IPV-005/003/018.

Features:
  - Custom TRACE level (5) for high-frequency audio loop events
  - SQLite black box (logs/voxinput_logging.db) with HM-IPV-018 turbo PRAGMAs
  - Batched SqliteHandler (100ms flush / 100 records)
  - Auto-trim on startup (TRACE/DEBUG 24h, INFO 7d, WARN 30d, ERROR/FATAL never)
  - sys.excepthook root crash handler → crash_artifacts table
  - Level from LOG_LEVEL env var → .env file → default (TRACE)

Usage:
    from src.logger import init_logging, get_logger
    init_logging("voxinput")
    log = get_logger(__name__)
    log.trace("audio_chunk", rms=420, level=0.3)
    log.info("listening_started")
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sqlite3
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

# ─── TRACE custom level ──────────────────────────────────────────────────────

TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]

# ─── Constants ────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
LOGS_DIR = ROOT_DIR / "logs"

# Retention per log level (seconds). None = keep forever.
_RETENTION: dict[str, float | None] = {
    "TRACE":   24 * 3600,
    "DEBUG":   24 * 3600,
    "INFO":    7 * 24 * 3600,
    "WARNING": 30 * 24 * 3600,
    "ERROR":   None,
    "FATAL":   None,
    "CRITICAL": None,
}

# Auto-trim every N inserts (not every call — cheap check)
_TRIM_EVERY_N = 1000

# SQLite turbo PRAGMAs (HM-IPV-018 §2.1)
_PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA cache_size = -131072;",       # 128MB
    "PRAGMA mmap_size = 536870912;",      # 512MB
    "PRAGMA temp_store = MEMORY;",
    "PRAGMA busy_timeout = 30000;",       # 30s
    "PRAGMA wal_autocheckpoint = 1000;",
    "PRAGMA foreign_keys = ON;",
    "PRAGMA secure_delete = OFF;",
    "PRAGMA optimize;",
]

_DDL = """
CREATE TABLE IF NOT EXISTS system_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL    NOT NULL,
    level     TEXT    NOT NULL,
    component TEXT    NOT NULL,
    event     TEXT    NOT NULL,
    trace_id  TEXT,
    payload   TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_time    ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level   ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_comp    ON system_logs(component);

CREATE TABLE IF NOT EXISTS crash_artifacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    REAL    NOT NULL,
    error_id     TEXT    NOT NULL,
    component    TEXT    NOT NULL,
    message      TEXT    NOT NULL,
    stack_trace  TEXT    NOT NULL,
    local_vars   TEXT,
    system_state TEXT,
    created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""


# ─── SQLite Handler ──────────────────────────────────────────────────────────

class SqliteHandler(logging.Handler):
    """
    Non-blocking SQLite log handler with batched writes.

    Accumulates records in an in-memory buffer and flushes to SQLite:
      - Every FLUSH_INTERVAL seconds (default 0.1s / 100ms)
      - When buffer reaches BATCH_SIZE records (default 100)
      - On handler close()

    Trim runs on startup and every TRIM_EVERY_N inserts.
    """

    FLUSH_INTERVAL = 0.1   # seconds
    BATCH_SIZE = 100

    def __init__(self, db_path: Path, component: str) -> None:
        super().__init__()
        self._db_path = db_path
        self._component = component
        self._buffer: list[tuple] = []
        self._lock = threading.Lock()
        self._insert_count = 0
        self._conn: sqlite3.Connection | None = None

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        for pragma in _PRAGMAS:
            try:
                self._conn.execute(pragma)
            except sqlite3.OperationalError:
                pass
        self._conn.executescript(_DDL)
        self._conn.commit()

        # Startup trim
        try:
            self._trim()
        except Exception:
            pass

        # Background flush thread
        self._stop = threading.Event()
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="log-flush"
        )
        self._flush_thread.start()

    # ── Logging.Handler interface ────────────────────────────────────────────

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            payload = json.dumps({
                "file": record.filename,
                "line": record.lineno,
                "func": record.funcName,
                "msg": msg,
            })
            row = (
                record.created,
                record.levelname,
                self._component,
                record.getMessage()[:200],  # event = first 200 chars of message
                None,                        # trace_id (future: correlation IDs)
                payload,
            )
            with self._lock:
                self._buffer.append(row)
                self._insert_count += 1
                should_flush = len(self._buffer) >= self.BATCH_SIZE
                should_trim  = self._insert_count % _TRIM_EVERY_N == 0

            if should_flush:
                self._flush_now()
            if should_trim:
                threading.Thread(target=self._trim, daemon=True).start()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self._stop.set()
        self._flush_thread.join(timeout=2.0)
        self._flush_now()
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        super().close()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _flush_loop(self) -> None:
        while not self._stop.wait(self.FLUSH_INTERVAL):
            self._flush_now()

    def _flush_now(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch, self._buffer = self._buffer, []

        if not self._conn or not batch:
            return
        try:
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO system_logs "
                    "(timestamp, level, component, event, trace_id, payload) "
                    "VALUES (?,?,?,?,?,?)",
                    batch
                )
        except Exception as e:
            sys.stderr.write(f"[logger] flush error: {e}\n")

    def _trim(self) -> None:
        """Delete rows older than their retention period. Vacuum after."""
        if not self._conn:
            return
        now = time.time()
        deleted = 0
        try:
            for level, max_age in _RETENTION.items():
                if max_age is None:
                    continue
                cutoff = now - max_age
                cur = self._conn.execute(
                    "DELETE FROM system_logs WHERE level = ? AND timestamp < ?",
                    (level, cutoff)
                )
                deleted += cur.rowcount
            if deleted:
                self._conn.execute("VACUUM;")
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                self._conn.commit()
        except Exception as e:
            sys.stderr.write(f"[logger] trim error: {e}\n")

    def write_crash_artifact(
        self,
        error_id: str,
        message: str,
        stack_trace: str,
        system_state: dict | None = None,
    ) -> None:
        """Write a crash artifact to crash_artifacts table (FATAL events)."""
        if not self._conn:
            return
        state_json = json.dumps(system_state or {})
        try:
            self._conn.execute(
                "INSERT INTO crash_artifacts "
                "(timestamp, error_id, component, message, stack_trace, system_state) "
                "VALUES (?,?,?,?,?,?)",
                (time.time(), error_id, self._component, message, stack_trace, state_json)
            )
            self._conn.commit()
        except Exception as e:
            sys.stderr.write(f"[logger] crash artifact write error: {e}\n")


# ─── Module-level state ───────────────────────────────────────────────────────

_sqlite_handler: SqliteHandler | None = None
_component: str = "voxinput"


# ─── Public API ───────────────────────────────────────────────────────────────

def _load_dotenv() -> dict[str, str]:
    """Load .env file from project root, return {KEY: VALUE} dict."""
    env: dict[str, str] = {}
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env


def _resolve_level(dotenv: dict[str, str]) -> int:
    """LOG_LEVEL from env var > .env file > TRACE default."""
    name = os.environ.get("LOG_LEVEL") or dotenv.get("LOG_LEVEL", "TRACE")
    name = name.upper()
    level_map = {
        "TRACE": TRACE,
        "DEBUG": logging.DEBUG,
        "INFO":  logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "FATAL": logging.CRITICAL,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(name, TRACE)


def init_logging(component: str = "voxinput") -> logging.Logger:
    """
    Initialise VoxInput logging. Call ONCE at application startup.

    Sets up:
      - Root logger at resolved level (TRACE by default)
      - Console StreamHandler (colourised level prefix)
      - SqliteHandler to logs/voxinput_logging.db
      - sys.excepthook root crash handler

    Args:
        component: Service name embedded in every log row.

    Returns:
        Root logger instance.
    """
    global _sqlite_handler, _component
    _component = component

    dotenv = _load_dotenv()
    level = _resolve_level(dotenv)

    db_path_str = os.environ.get("LOG_DB_PATH") or dotenv.get("LOG_DB_PATH", "")
    db_path = Path(db_path_str) if db_path_str else LOGS_DIR / "voxinput_logging.db"

    log_console = (os.environ.get("LOG_CONSOLE") or dotenv.get("LOG_CONSOLE", "true")).lower() != "false"

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers (avoid duplicate output on re-init)
    root.handlers.clear()

    # Console handler
    if log_console:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(name)s — %(message)s",
            datefmt="%H:%M:%S"
        )
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        ch.setLevel(level)
        root.addHandler(ch)

    # Rotating file handler (plain text, 5MB × 3)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "voxinput.log"
    fh = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=5_000_000, backupCount=3
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s %(funcName)s:%(lineno)d — %(message)s"
    ))
    fh.setLevel(level)
    root.addHandler(fh)

    # SQLite handler
    _sqlite_handler = SqliteHandler(db_path, component)
    _sqlite_handler.setLevel(level)
    root.addHandler(_sqlite_handler)

    # Install root exception hook
    _install_excepthook(component)

    logger = logging.getLogger(component)
    logger.info("logging_initialized component=%s level=%s db=%s",
                component, logging.getLevelName(level), db_path)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a named logger. Call after init_logging()."""
    return logging.getLogger(name or _component)


def get_sqlite_handler() -> SqliteHandler | None:
    """Return the active SqliteHandler (for crash artifact writes)."""
    return _sqlite_handler


# ─── Root exception hook ──────────────────────────────────────────────────────

def _install_excepthook(component: str) -> None:
    """Install sys.excepthook to catch all unhandled exceptions."""

    def _hook(exctype: type, value: BaseException, tb: Any) -> None:
        # Don't trap KeyboardInterrupt — let it exit cleanly
        if issubclass(exctype, KeyboardInterrupt):
            sys.__excepthook__(exctype, value, tb)
            return

        import uuid
        error_id = f"crash-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        trace = "".join(traceback.format_exception(exctype, value, tb))
        state = {
            "python": sys.version,
            "platform": sys.platform,
            "argv": sys.argv,
            "pid": os.getpid(),
        }
        sys.stderr.write(f"\n[FATAL] {error_id}\n{trace}\n")

        # Write crash artifact to SQLite
        handler = get_sqlite_handler()
        if handler:
            handler.write_crash_artifact(error_id, str(value), trace, state)
            handler.close()  # Flush before exit

        # Log to root logger too
        logging.getLogger(component).critical(
            "UNHANDLED EXCEPTION error_id=%s exc=%s", error_id, str(value)
        )
        sys.exit(1)

    sys.excepthook = _hook
