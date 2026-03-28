---
id: GOV-006
title: "Logging Specification"
type: reference
status: APPROVED
owner: architect
agents: [all]
tags: [coding, standards, governance, quality, safety]
related: [GOV-003, GOV-004]
created: 2026-03-04
updated: 2026-03-04
version: 2.0.0
---

> **BLUF:** NASA/JPL-grade logging specification. Every application event is a structured, queryable record — not a text line. Logs go to databases or flat files per the application spec. Trace logs are mandatory for agent-readable execution reconstruction. Covers Python, C/C++, and TypeScript with exhaustive log level definitions, retention policies, correlation IDs, and forensic query patterns. No `print()`. No unstructured text. No silent execution.

# Logging Specification: "The Flight Recorder"

> **"If it isn't in the log, it didn't happen."**
> *— Adapted from Aviation Investigation Protocol (NTSB)*

---

## 1. The Logging Laws

1. **Structured Only** — Every log is a machine-parseable record (JSON). No free-text lines. An agent must be able to query logs without regex.
2. **Trace Is King** — Trace-level logs must enable an agent to reconstruct exactly what an application did, step by step, input to output.
3. **Log to Storage** — All logs go to databases (SQLite, PostgreSQL) or structured flat files (JSONL) per the application specification. Never ephemeral-only.
4. **Correlate Everything** — Every log carries a correlation ID that links it across service boundaries.
5. **No Silent Execution** — Every function entry/exit in critical paths, every external call, every state change must be logged at TRACE or DEBUG.
6. **Never Block** — Logging must never block the application's hot path. Use async/buffered writes.
7. **Sanitize Always** — Never log secrets, passwords, tokens, PII, or credentials.

---

## 2. Log Levels (RFC 5424 Aligned)

Strict definitions. Every developer and agent must agree on what each level means.

| Level | Numeric | Definition | When to Use | Retention |
|:------|:--------|:-----------|:------------|:----------|
| **TRACE** | 5 | Finest-grain execution detail | Function entry/exit, loop iterations, variable values, raw I/O | **Circular buffer** or 24h |
| **DEBUG** | 10 | Diagnostic information for developers | State transitions, config loaded, cache hit/miss | **24 hours** |
| **INFO** | 20 | Significant lifecycle events | Service start/stop, job completed, user login | **7 days** |
| **WARN** | 30 | Anomalous but handled condition | Retry succeeded, deprecated API called, slow query | **30 days** |
| **ERROR** | 40 | Failure requiring attention | Exception caught, operation failed, data inconsistency | **Forever** |
| **FATAL** | 50 | Unrecoverable — application will exit | OOM, corrupt state, safety violation | **Forever** |

### 2.1 The TRACE Level — Why It Matters

> **Trace logs are the black box flight recorder.** When something fails, an agent can read the trace and know exactly what happened — every function call, every decision branch, every value.

```python
# TRACE-level logging in a critical function
logger.trace("calculate_route.enter", origin=origin, destination=dest, algorithm="a_star")
# ... computation ...
logger.trace("calculate_route.pathfound", nodes_explored=142, path_length_m=23.5, elapsed_ms=4.2)
logger.trace("calculate_route.exit", success=True)
```

**When an agent reads this**, it knows:
- What function was called, with what inputs
- What the function computed internally
- What it returned and how long it took

### 2.2 Production Level Override

| Environment | Default Level | Override |
|:------------|:-------------|:---------|
| Production | **WARN** | Set `LOG_LEVEL=INFO` for visibility |
| Staging | **INFO** | Set `LOG_LEVEL=DEBUG` for diagnostics |
| Development | **DEBUG** | Set `LOG_LEVEL=TRACE` for full trace |
| Testing | **TRACE** | Always — full forensic capture |

---

## 3. Structured Log Schema

Every log record MUST conform to this schema. No exceptions.

### 3.1 Required Fields

| Field | Type | Description | Example |
|:------|:-----|:-----------|:--------|
| `timestamp` | ISO 8601 (UTC) | When the event occurred, microsecond precision | `2026-03-04T10:15:30.123456Z` |
| `level` | string | Log level name | `INFO` |
| `service` | string | Application/service name | `auth-service` |
| `event` | string | Short, dot-separated event name | `user.login.success` |
| `correlation_id` | string | Request trace ID (from GOV-004 §8) | `req-a1b2c3d4e5f6` |
| `message` | string | Human-readable description | `User logged in successfully` |

### 3.2 Optional Contextual Fields

| Field | Type | Description |
|:------|:-----|:-----------|
| `component` | string | Sub-module within the service |
| `function` | string | Function name that emitted the log |
| `file` | string | Source file |
| `line` | integer | Source line number |
| `duration_ms` | float | Operation duration |
| `error_id` | string | Reference to GOV-004 ErrorContext |
| `user_id` | string | Sanitized user identifier |
| `payload` | object | Structured key-value context data |

### 3.3 Example Log Record (JSON)

```json
{
  "timestamp": "2026-03-04T10:15:30.123456Z",
  "level": "INFO",
  "service": "order-service",
  "event": "order.created",
  "correlation_id": "req-a1b2c3d4e5f6",
  "message": "New order created",
  "component": "order_handler",
  "function": "create_order",
  "file": "order_handler.py",
  "line": 87,
  "duration_ms": 12.4,
  "payload": {
    "order_id": "ord-789",
    "item_count": 3,
    "total_cents": 4599
  }
}
```

---

## 4. Log Storage Destinations

Logs go to **persistent storage** — never just stdout. The application specification determines the destination.

### 4.1 Destination Matrix

| Application Type | Primary Storage | Secondary (Fallback) | Format |
|:-----------------|:---------------|:--------------------|:-------|
| **Embedded / Local** | SQLite database | JSONL flat file | Structured JSON |
| **Web Service** | Central logging service (ELK, Loki, CloudWatch) | JSONL flat file | Structured JSON |
| **CLI Tool** | JSONL flat file | stderr (structured) | Structured JSON |
| **Desktop / GUI** | SQLite database | JSONL flat file | Structured JSON |
| **Batch / Pipeline** | JSONL flat file per run | SQLite if persistent | Structured JSON |

### 4.2 SQLite Schema (For Database Storage)

```sql
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601 UTC
    level TEXT NOT NULL,               -- TRACE, DEBUG, INFO, WARN, ERROR, FATAL
    service TEXT NOT NULL,             -- Application name
    event TEXT NOT NULL,               -- Dot-separated event name
    correlation_id TEXT,               -- Request trace ID
    message TEXT,                      -- Human-readable
    payload JSON                       -- Full structured context
);

-- Required indexes for forensic queries
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_correlation ON system_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_logs_event ON system_logs(event);
CREATE INDEX IF NOT EXISTS idx_logs_service ON system_logs(service);
```

### 4.3 JSONL Flat File (For File Storage)

One JSON object per line. File naming: `{service}_{date}.log`

```
{"timestamp":"2026-03-04T10:15:30.123456Z","level":"INFO","service":"api","event":"request.start","correlation_id":"req-abc","message":"GET /users","payload":{"method":"GET","path":"/users"}}
{"timestamp":"2026-03-04T10:15:30.234567Z","level":"INFO","service":"api","event":"request.complete","correlation_id":"req-abc","message":"200 OK","payload":{"status":200,"duration_ms":111.1}}
```

### 4.4 SQLite Performance Configuration

```sql
PRAGMA journal_mode = WAL;         -- Concurrent reads during writes
PRAGMA synchronous = NORMAL;       -- Safe fsync speedup
PRAGMA temp_store = MEMORY;        -- Temp tables in RAM
PRAGMA cache_size = -64000;        -- 64MB page cache
PRAGMA busy_timeout = 5000;        -- Wait 5s before lock failure
PRAGMA mmap_size = 268435456;      -- 256MB memory-mapped I/O
```

---

## 5. Python Logging Implementation

### 5.1 Structlog Setup (Mandatory)

```python
"""Logging configuration — call at application startup BEFORE any other imports."""

import structlog
import logging
import sys
import json
from pathlib import Path
from contextvars import ContextVar

# Correlation ID from GOV-004 §8
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

def configure_logging(
    service_name: str,
    level: str = "WARN",
    log_db_path: Path | None = None,
    log_file_path: Path | None = None,
) -> None:
    """Initialize structured logging for a service.

    Args:
        service_name: Name of this service (e.g., "order-service").
        level: Minimum log level (TRACE, DEBUG, INFO, WARN, ERROR, FATAL).
        log_db_path: Path to SQLite database (if using DB storage).
        log_file_path: Path to JSONL file (if using file storage).
    """
    level = os.environ.get("LOG_LEVEL", level).upper()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _add_service_context(service_name),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            _level_to_int(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
```

### 5.2 Usage Patterns

```python
import structlog

logger = structlog.get_logger()

# INFO: Lifecycle events
logger.info("service.started", version="1.0.0", port=8080)

# WARN: Anomalous but handled
logger.warning("cache.miss", key="user_123", fallback="database")

# ERROR: Failure (always include exc_info for stack trace)
try:
    result = database.query(sql)
except DatabaseError:
    logger.exception("database.query_failed", sql=sql)  # Auto-includes stack trace

# TRACE: Execution reconstruction (critical for agent debugging)
logger.debug("calculate_route.enter", origin=origin, destination=dest)
logger.debug("calculate_route.exit", path_length=result.length, elapsed_ms=elapsed)
```

### 5.3 The `@trace_execution` Decorator

For critical code paths, zero-boilerplate trace logging:

```python
import functools
import time
import structlog

def trace_execution(func):
    """Decorator that logs function entry, exit, and exceptions at TRACE level."""
    logger = structlog.get_logger()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        logger.debug(f"{func_name}.enter", args_count=len(args), kwargs_keys=list(kwargs.keys()))
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(f"{func_name}.exit", elapsed_ms=round(elapsed, 2), success=True)
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"{func_name}.exception", elapsed_ms=round(elapsed, 2), error=str(e), exc_info=True)
            raise
    return wrapper
```

### 5.4 Python Tools

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| `structlog` | Structured logging library | Required |
| `python-json-logger` | JSON formatter for stdlib logging | Alternative |
| Custom scanner | Detect `print()` statements in production code | HARD FAIL |

---

## 6. TypeScript / Node.js Logging Implementation

### 6.1 Pino Setup (Mandatory)

```typescript
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL?.toLowerCase() ?? 'warn',
  formatters: {
    level: (label: string) => ({ level: label.toUpperCase() }),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  base: {
    service: process.env.SERVICE_NAME ?? 'unknown',
  },
  // Write to file in production
  transport: process.env.LOG_FILE
    ? { target: 'pino/file', options: { destination: process.env.LOG_FILE } }
    : undefined,
});

export default logger;
```

### 6.2 Usage Patterns

```typescript
import logger from './logger';

// INFO: Lifecycle
logger.info({ port: 8080 }, 'server.started');

// ERROR: With context
logger.error({ err, userId, endpoint }, 'request.failed');

// TRACE: Execution reconstruction
logger.trace({ input, step: 'validation' }, 'process_order.enter');
logger.trace({ output, elapsed_ms: 12.4 }, 'process_order.exit');
```

### 6.3 TypeScript Tools

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| `pino` | High-performance structured logger | Required |
| `pino-pretty` | Dev-mode human-readable output | Dev only |
| ESLint `no-console` rule | Detect `console.log` in production | HARD FAIL |

---

## 7. C/C++ Logging Implementation

### 7.1 spdlog Setup (Mandatory)

```cpp
#include <spdlog/spdlog.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <nlohmann/json.hpp>

/**
 * Initialize structured logging for a C++ service.
 *
 * @param service_name  Name of this service (e.g., "motor-controller").
 * @param log_file      Path to JSONL log file.
 * @param level         Minimum log level.
 */
void init_logging(const char *service_name, const char *log_file, spdlog::level::level_enum level) {
    auto file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(log_file, true);
    auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();

    auto logger = std::make_shared<spdlog::logger>(
        service_name,
        spdlog::sinks_init_list{file_sink, console_sink}
    );
    logger->set_level(level);
    spdlog::set_default_logger(logger);
}
```

### 7.2 Structured Log Macro

```cpp
#define LOG_STRUCTURED(level, event, ...) \
    do { \
        nlohmann::json _log_payload = {__VA_ARGS__}; \
        _log_payload["event"] = event; \
        _log_payload["timestamp"] = get_iso_timestamp(); \
        spdlog::log(level, _log_payload.dump()); \
    } while(0)

/* Usage */
LOG_STRUCTURED(spdlog::level::info, "motor.command",
    {"velocity_mps", 1.5},
    {"direction", "forward"}
);
```

### 7.3 C/C++ Tools

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| `spdlog` | Fast C++ logging library | Required |
| `nlohmann/json` | JSON serialization | Required |
| Custom scanner | Detect `printf`/`fprintf` in production | HARD FAIL |

---

## 8. Trace Instrumentation Requirements

Every critical module **MUST** emit trace-level logs for agent reconstruction.

### 8.1 What Must Be Traced

| Category | Required Trace Events | Example Fields |
|:---------|:---------------------|:---------------|
| **Function entry/exit** | Every public function in critical paths | `function`, `args`, `return_value`, `elapsed_ms` |
| **External calls** | Every HTTP request, DB query, file I/O | `endpoint`, `method`, `status`, `duration_ms` |
| **State changes** | Every state machine transition | `from_state`, `to_state`, `trigger` |
| **Decision points** | Every if/else in business logic | `condition`, `branch_taken`, `values` |
| **Data transformations** | Input → Output for critical transforms | `input_shape`, `output_shape`, `records_processed` |
| **Configuration loads** | Every config file/env var read | `source`, `key`, `value` (sanitized) |
| **Queue/Message operations** | Every enqueue/dequeue | `queue_name`, `message_type`, `queue_depth` |

### 8.2 Trace Event Naming Convention

Use dot-separated hierarchical names:

```
{component}.{operation}.{phase}
```

| Phase | When |
|:------|:-----|
| `.enter` | Function/operation starts |
| `.exit` | Function/operation completes normally |
| `.error` | Function/operation fails |
| `.decision` | Branch point reached |
| `.checkpoint` | Intermediate state recorded |

Examples: `auth.login.enter`, `database.query.exit`, `router.match.decision`

---

## 9. Log Rotation & Retention

### 9.1 Retention Policy

| Level | Retention | Rationale |
|:------|:----------|:----------|
| TRACE | **24 hours** or circular buffer | Volume too high for permanent storage |
| DEBUG | **24 hours** | Development diagnostics only |
| INFO | **7 days** | Lifecycle tracking |
| WARN | **30 days** | Pattern detection |
| ERROR | **Forever** | Forensic evidence — never delete |
| FATAL | **Forever** | Forensic evidence — never delete |

### 9.2 Rotation Rules

- **File storage**: New file daily. Name: `{service}_{YYYY-MM-DD}.log`
- **Database storage**: Run retention cleanup daily (cron or scheduled task)
- **Compressed archive**: WARN+ logs archived to `.gz` after retention period
- **ERROR/FATAL**: Migrated to permanent archive, never auto-deleted

### 9.3 Retention Script (Python Reference)

```python
"""Log retention — run daily via cron or scheduler."""

import sqlite3
import time
from pathlib import Path

RETENTION_SECONDS = {
    "TRACE": 24 * 3600,      # 24 hours
    "DEBUG": 24 * 3600,      # 24 hours
    "INFO":  7 * 24 * 3600,  # 7 days
    "WARN": 30 * 24 * 3600,  # 30 days
    # ERROR and FATAL: Never deleted
}

def run_retention(db_path: Path) -> dict[str, int]:
    """Delete logs older than their retention period."""
    conn = sqlite3.connect(db_path)
    now = time.time()
    results = {}
    for level, max_age in RETENTION_SECONDS.items():
        cutoff = now - max_age
        cursor = conn.execute(
            "DELETE FROM system_logs WHERE level = ? AND timestamp < datetime(?, 'unixepoch')",
            (level, cutoff),
        )
        results[level] = cursor.rowcount
    conn.commit()
    conn.close()
    return results
```

---

## 10. Forensic Query Patterns

### 10.1 Standard Queries

| Need | Query |
|:-----|:------|
| **"Show me the crash"** | `SELECT * FROM system_logs WHERE level IN ('ERROR','FATAL') ORDER BY timestamp DESC LIMIT 20;` |
| **"Trace request X"** | `SELECT * FROM system_logs WHERE correlation_id = 'req-abc' ORDER BY timestamp;` |
| **"What happened in the last 5 min"** | `SELECT * FROM system_logs WHERE timestamp > datetime('now','-5 minutes');` |
| **"All events for service Y"** | `SELECT * FROM system_logs WHERE service = 'auth-service' ORDER BY timestamp DESC LIMIT 100;` |
| **"Error frequency by hour"** | `SELECT strftime('%H',timestamp) as hour, COUNT(*) FROM system_logs WHERE level='ERROR' GROUP BY hour;` |

### 10.2 Agent Reconstruction Query

An agent reading logs to understand what happened:

```sql
-- Reconstruct the full execution trace for a single request
SELECT timestamp, level, event, message, payload
FROM system_logs
WHERE correlation_id = 'req-a1b2c3d4e5f6'
ORDER BY timestamp ASC;
```

This gives the agent a chronological, structured narrative of everything the application did for that request.

---

## 11. Environment Variables

| Variable | Default | Description |
|:---------|:--------|:-----------|
| `LOG_LEVEL` | `WARN` | Minimum log level: TRACE, DEBUG, INFO, WARN, ERROR, FATAL |
| `LOG_DB_PATH` | *(none)* | Path to SQLite logging database |
| `LOG_FILE_PATH` | *(none)* | Path to JSONL log file |
| `LOG_CONSOLE` | `true` | Also output to stderr |
| `LOG_RETENTION_DAYS` | `7` | Auto-cleanup period for INFO-level logs |
| `SERVICE_NAME` | *(required)* | Application/service name for log records |

**Override precedence**: Environment variables > `.env` file > code defaults.

---

## 12. Forbidden Patterns

| Pattern | Why Forbidden | Alternative |
|:--------|:-------------|:------------|
| `print()` / `printf()` / `console.log()` | Not captured in storage, not structured | Use the logger |
| `logger.info(f"User {name}")` | String interpolation before call — wasteful if filtered | `logger.info("user.login", name=name)` |
| Unstructured text messages | Cannot query, filter, or parse | Always use key-value structured data |
| Logging to stdout only | Ephemeral — lost on restart | Always write to persistent storage |
| Logging secrets/passwords/tokens | Security breach | Sanitize all payloads |
| Logging inside tight loops without sampling | Generates excessive volume | Sample or use circular buffer |
| Bare `except` without logging | Violates GOV-004 Law #6 | Always `logger.exception()` |

---

## 13. Performance Requirements

| Metric | Requirement |
|:-------|:-----------|
| Log call latency (non-blocking) | < 50 µs per call |
| Aggregator throughput | > 10,000 logs/second sustained |
| Query latency (indexed, 1M rows) | < 100 ms |
| Log file write flush | ≤ 1 second (buffered) |
| Zero-loss at ERROR/FATAL | Guaranteed — sync flush on ERROR+ |

---

## 14. Test Integration

### 14.1 Testing Log Level

Tests **MUST** run at TRACE level automatically:

```python
# conftest.py
import os
os.environ["LOG_LEVEL"] = "TRACE"
```

### 14.2 Post-Test Log Audit

After every test, check for unexpected ERROR/FATAL entries:

```python
@pytest.fixture(autouse=True)
def check_logs_after_test(log_db):
    """Fail the test if ERROR/FATAL logs were emitted."""
    yield
    errors = log_db.execute(
        "SELECT * FROM system_logs WHERE level IN ('ERROR', 'FATAL')"
    ).fetchall()
    if errors:
        for err in errors:
            print(f"  ❌ [{err['level']}] {err['event']}: {err['message']}")
        pytest.fail(f"{len(errors)} unexpected error(s) in logs")
```

---

## 15. Compliance Checklist

Before deploying any service:

- [ ] Structured logging library configured at startup (structlog / pino / spdlog)
- [ ] All log calls use structured key-value pairs — no string formatting
- [ ] Log storage destination defined (database or JSONL file)
- [ ] Correlation ID from GOV-004 §8 included in every log
- [ ] TRACE-level instrumentation covers all critical paths (§8)
- [ ] No `print()` / `printf()` / `console.log()` in production code
- [ ] Log rotation and retention configured per §9
- [ ] ERROR/FATAL logs trigger immediate flush (never buffered away)
- [ ] Performance meets §13 requirements (< 50 µs per call)
- [ ] Secrets/PII never appear in log payloads
- [ ] Tests run at TRACE level with post-test audit (§14)
- [ ] Environment variables documented in `.env.example`

---

## 16. Agent Instructions

When an architect asks you to "set up logging" or "add logging," follow this protocol:

1. **Choose logging library** — Python: structlog, TypeScript: pino, C++: spdlog (§5-7)
2. **Configure at startup** — Initialize before any other code runs
3. **Define storage destination** — Database or JSONL per application type (§4)
4. **Set up log schema** — Create SQLite tables or JSONL format (§4.2-4.3)
5. **Instrument critical paths** — Add TRACE-level logs per §8
6. **Wire correlation IDs** — Connect to GOV-004 §8 correlation system
7. **Add `@trace_execution` decorator** to critical functions (§5.3)
8. **Configure retention** — Daily cleanup cron/scheduler (§9)
9. **Add forbidden pattern scanner** — CI must reject `print()` statements (§12)
10. **Set up test integration** — TRACE level + post-test audit (§14)
11. **Document env variables** — Create `.env.example` (§11)

---

> **"A log is not a message. It is a fact, recorded in a structure, queryable by any machine."**
