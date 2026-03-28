---
id: GOV-004
title: "Error Handling Protocol"
type: reference
status: APPROVED
owner: architect
agents: [all]
tags: [coding, standards, governance, quality, safety]
related: [GOV-002, GOV-003]
created: 2026-03-04
updated: 2026-03-04
version: 2.0.0
---

> **BLUF:** NASA/JPL-grade error handling protocol. Zero-dark-failure doctrine: no error happens silently, no application crashes without a trace. Every exception is caught, classified by severity level (DO-178C DAL mapping), logged with full stack trace and context, and either recovered from or escalated. Includes FMEA requirements, crash artifacts, circuit breakers, correlation IDs, and mandatory post-incident review.

# Error Handling Protocol: "No Error in the Dark"

> **"The Mars Pathfinder was saved because it logged its own crash."**

---

## 1. The Error Laws

1. **No Silent Deaths** — Every error is caught, logged, and handled. An error that happens in the dark is a bomb with a delayed fuse.
2. **Stack Traces Are Sacred** — Every logged error includes the full stack trace. A message without a trace is worthless for debugging.
3. **Catch at the Root** — Every application entry point installs a global exception handler. Nothing escapes to the OS unlogged.
4. **Log Everything** — All errors go to structured logs and/or databases as defined by the application specification.
5. **Fail Loud, Fail Safe** — When recovery isn't possible, fail visibly (alert, log, notify) and enter a safe degraded state.
6. **No `except: pass`** — Swallowing errors is forbidden. Static analysis scanners enforce this with zero tolerance.
7. **Correlate Across Boundaries** — Every error carries a correlation ID that traces it from origin through every service it touches.

---

## 2. Error Taxonomy

All errors are classified by **Category** and **Severity**. This drives automated recovery decisions.

| Category | Description | Retry Strategy | Severity |
|:---------|:------------|:---------------|:---------|
| **VALIDATION** | Bad input (wrong type, missing field, out of range) | NO_RETRY | LOW |
| **BUSINESS_LOGIC** | Domain rule violation (duplicate entry, invalid state) | NO_RETRY | MEDIUM |
| **EXTERNAL_SERVICE** | Third-party API failure (timeout, 5xx) | EXPONENTIAL_BACKOFF | HIGH |
| **DATABASE** | Data layer failure (connection lost, lock timeout) | EXPONENTIAL_BACKOFF | HIGH |
| **RESOURCE** | Missing resource (file not found, model missing) | NO_RETRY | LOW |
| **INFRASTRUCTURE** | System exhaustion (OOM, disk full, port in use) | CRASH + Restart | CRITICAL |
| **CONFIGURATION** | Invalid startup config (parse failure, missing env var) | CRASH immediately | CRITICAL |
| **NETWORK** | Connection failure, DNS resolution, TLS errors | RETRY with backoff | HIGH |
| **SECURITY** | Auth failure, permission denied, token expired | NO_RETRY + Alert | HIGH |
| **HARDWARE** | Sensor/actuator failure, device timeout | SAFE_STOP + Alert | CRITICAL |
| **FATAL** | Unrecoverable — data corruption, safety breach | EMERGENCY_STOP | CRITICAL |
| **TRANSIENT** | Temporary glitch (noise, blip, race condition) | IMMEDIATE (max 3x) | LOW |
| **UNKNOWN** | Uncaught generic exception | NO_RETRY + Log + Alert | HIGH |

---

## 3. Severity Levels (DO-178C Table A-1)

Every error has a **Category** (what went wrong) and a **Severity Level** (how bad it is). The severity drives response requirements.

| Level | Name | Definition | Response Requirements | DAL Equivalent |
|:------|:-----|:-----------|:---------------------|:---------------|
| **1** | **CATASTROPHIC** | Data loss, safety breach, physical harm possible | EMERGENCY_STOP. Crash artifact. Immediate human notification. Full post-incident review. | DAL-A |
| **2** | **HAZARDOUS** | Major function lost, security compromised | Immediate safe-state. Crash artifact. Alert on-call. Post-incident review within 24h. | DAL-B |
| **3** | **MAJOR** | Significant degradation, data integrity at risk | Log ERROR. Alert. Automated recovery attempt. Review within 1 sprint. | DAL-C |
| **4** | **MINOR** | Reduced capability, user inconvenience | Log WARN. Retry if applicable. Track for patterns. | DAL-D |
| **5** | **NO EFFECT** | Cosmetic, logged for completeness | Log INFO. No action required. | DAL-E |

### 3.1 Mapping Categories to Severity

| Category | Default Severity | Can Escalate To |
|:---------|:----------------|:----------------|
| FATAL | **1 — CATASTROPHIC** | — |
| HARDWARE | **2 — HAZARDOUS** | 1 if safety-critical |
| INFRASTRUCTURE | **2 — HAZARDOUS** | 1 if data loss |
| CONFIGURATION | **3 — MAJOR** | 2 if at runtime |
| SECURITY | **3 — MAJOR** | 1 if breach confirmed |
| EXTERNAL_SERVICE | **3 — MAJOR** | 2 if critical dependency |
| DATABASE | **3 — MAJOR** | 1 if data corruption |
| NETWORK | **4 — MINOR** | 3 if persistent |
| BUSINESS_LOGIC | **4 — MINOR** | 3 if data integrity |
| VALIDATION | **5 — NO EFFECT** | 4 if frequent |
| TRANSIENT | **5 — NO EFFECT** | 3 if pattern detected |
| UNKNOWN | **3 — MAJOR** | 1 pending investigation |

---

## 3. Structured Error Context

Every error must carry structured context. Never throw a bare string.

### 3.1 Python

```python
from dataclasses import dataclass, field
from uuid import uuid4
from enum import Enum, auto
from typing import Any

class ErrorCategory(Enum):
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

@dataclass
class ErrorContext:
    """Structured context attached to every application error."""
    error_id: str = field(default_factory=lambda: f"err-{uuid4().hex[:12]}")
    category: ErrorCategory = ErrorCategory.UNKNOWN
    operation: str | None = None       # e.g., "user_login"
    component: str | None = None       # e.g., "auth-service"
    correlation_id: str | None = None  # Request trace ID
    input_data: dict[str, Any] | None = None  # Sanitized inputs (NO secrets)
    retryable: bool = False

class ApplicationError(Exception):
    """Base exception for all application errors."""
    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.context = context or ErrorContext()
        self.__cause__ = cause
```

### 3.2 TypeScript

```typescript
interface ErrorContext {
  errorId: string;
  category: ErrorCategory;
  operation?: string;
  component?: string;
  correlationId?: string;
  inputData?: Record<string, unknown>;
  retryable: boolean;
}

class ApplicationError extends Error {
  public readonly context: ErrorContext;
  public readonly cause?: Error;

  constructor(message: string, context: Partial<ErrorContext> = {}, cause?: Error) {
    super(message);
    this.name = 'ApplicationError';
    this.context = {
      errorId: `err-${crypto.randomUUID().slice(0, 12)}`,
      category: ErrorCategory.UNKNOWN,
      retryable: false,
      ...context,
    };
    this.cause = cause;
  }
}
```

### 3.3 C

```c
typedef struct {
    char error_id[32];
    error_category_t category;
    const char *operation;
    const char *component;
    const char *message;
    int error_code;
    bool retryable;
} error_context_t;

/* Initialize with defaults */
error_context_t error_new(error_category_t cat, const char *msg);

/* Log error with full context and stack trace */
void error_log(const error_context_t *ctx);
```

---

## 4. The Root Catch — Global Exception Handlers

**Every application entry point MUST install a global exception handler.** This is the safety net that ensures no error ever escapes to the void.

### 4.1 Python

```python
import sys
import traceback
import structlog

logger = structlog.get_logger(__name__)

def global_exception_handler(exctype, value, tb):
    """Last-resort handler. No error escapes unlogged."""
    trace = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(
        "UNHANDLED EXCEPTION — application will exit",
        error_type=exctype.__name__,
        error_message=str(value),
        stack_trace=trace,
        # Include error context if it's an ApplicationError
        error_context=getattr(value, 'context', None),
    )
    # Write crash artifact to database/file (see §6)
    write_crash_artifact(exctype, value, tb)
    sys.exit(1)

if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    # ... start application ...
```

### 4.2 TypeScript / Node.js

```typescript
process.on('uncaughtException', (error: Error) => {
  logger.fatal('UNHANDLED EXCEPTION', {
    error: error.message,
    stack: error.stack,
    context: (error as ApplicationError).context ?? {},
  });
  writeCrashArtifact(error);
  process.exit(1);
});

process.on('unhandledRejection', (reason: unknown) => {
  logger.fatal('UNHANDLED PROMISE REJECTION', { reason });
  process.exit(1);
});
```

### 4.3 C

```c
#include <signal.h>

void crash_handler(int signum) {
    /* Log signal, dump stack trace, flush logs */
    error_context_t ctx = error_new(ERROR_FATAL, "Signal received");
    ctx.error_code = signum;
    error_log(&ctx);
    /* Attempt stack trace via backtrace() */
    dump_backtrace();
    _exit(1);
}

int main(int argc, char *argv[]) {
    signal(SIGSEGV, crash_handler);
    signal(SIGABRT, crash_handler);
    signal(SIGFPE, crash_handler);
    /* ... */
}
```

---

## 5. Error Propagation Rules

### 5.1 The Propagation Ladder

```
Function → Catches specific errors it can handle
    ↓ (uncaught errors propagate up)
Module → Catches errors at service boundary, adds context
    ↓ (still uncaught? keep going)
Service Entry → Catches all remaining, logs crash artifact
    ↓ (truly unhandled)
Global Handler → Last resort. Logs. Exits.
```

### 5.2 Rules

1. **Catch only what you can handle** — Don't catch an error just to re-raise it.
2. **Add context as you propagate** — Each layer adds its own context (operation, component).
3. **Preserve the original cause** — Always chain exceptions (`raise ... from original`).
4. **Never catch and ignore** — If you catch it, you must log it, handle it, or re-raise it.
5. **Narrow catches** — Catch the most specific exception type, never bare `Exception`.

```python
# ✅ GOOD: Catch specific, add context, chain cause
try:
    result = database.query(sql)
except DatabaseConnectionError as e:
    raise ApplicationError(
        "Failed to fetch user data",
        context=ErrorContext(
            category=ErrorCategory.DATABASE,
            operation="get_user",
            component="user-service",
            retryable=True,
        ),
        cause=e,  # Original stack trace preserved
    ) from e

# ❌ BAD: Catch-all, swallow error
try:
    result = database.query(sql)
except Exception:
    pass  # FORBIDDEN — static scanner will reject this
```

---

## 6. Crash Artifacts

When a FATAL or unhandled error occurs, the system generates a **Crash Artifact** — a forensic record for post-incident analysis.

### 6.1 Required Fields

| Field | Content |
|:------|:--------|
| `timestamp` | ISO 8601 with microseconds |
| `error_id` | Unique identifier (e.g., `err-a1b2c3d4e5f6`) |
| `correlation_id` | Request trace ID (if available) |
| `component` | Service/module name |
| `category` | From error taxonomy |
| `message` | Human-readable error description |
| `stack_trace` | **Full** stack trace — every frame |
| `local_vars` | Sanitized local variables (NO secrets, passwords, tokens) |
| `system_state` | Runtime version, OS, memory usage, uptime |
| `input_data` | Sanitized input that triggered the error |

### 6.2 Storage

Crash artifacts are stored per the application specification. Common destinations:

| Destination | When |
|:------------|:-----|
| **Structured log** (JSON to stdout) | Always — minimum requirement |
| **SQLite database** | Embedded/local applications |
| **Central logging service** (ELK, Loki) | Distributed systems |
| **Error tracking service** (Sentry) | Web applications |
| **File system** (`crashes/` directory) | Fallback when all else fails |

**Agent Rule**: When setting up a new project, the crash artifact destination MUST be defined in the project specification. If no specification exists, default to structured JSON logs + file system fallback.

---

## 7. Recovery Strategies

### 7.1 Strategy Matrix

| Category | Immediate Action | Recovery | Escalation |
|:---------|:----------------|:---------|:-----------|
| **VALIDATION** | Return error response (400) | None needed | Log WARN |
| **TRANSIENT** | Retry immediately, max 3 attempts | Continue if success | Log WARN after 3 failures |
| **EXTERNAL_SERVICE** | Exponential backoff: 1s, 2s, 4s, 8s | Circuit breaker after 5 consecutive | Log ERROR + alert |
| **DATABASE** | Retry with backoff | Fallback to read-only/cache | Log ERROR + alert |
| **NETWORK** | Retry with backoff, max 5 | Degrade gracefully | Log ERROR |
| **SECURITY** | Reject immediately | None — do not retry auth | Log WARN + audit trail |
| **INFRASTRUCTURE** | Stop accepting new work | Restart process | Log CRITICAL + alert |
| **CONFIGURATION** | Crash immediately at startup | Fix config, restart | Log CRITICAL |
| **HARDWARE** | Enter SAFE_STOP state | Wait for human intervention | Log CRITICAL + alert |
| **FATAL** | EMERGENCY_STOP immediately | Write crash artifact, exit | Log CRITICAL + alert |

### 7.2 Circuit Breaker Pattern

For external dependencies that may fail repeatedly:

```
CLOSED → (failures < threshold) → continue calling
OPEN   → (failures ≥ threshold) → stop calling, return fallback
HALF-OPEN → (after cooldown) → try one call, if success → CLOSED, else → OPEN
```

| Parameter | Default |
|:----------|:--------|
| Failure threshold | 5 consecutive failures |
| Cooldown period | 30 seconds |
| Half-open retry | 1 attempt |

---

## 8. Correlation IDs

Every request entering the system gets a **correlation ID** that follows it through every service, log entry, and error report.

### 8.1 Rules

1. **Generate at ingress** — The first service to receive a request generates the correlation ID
2. **Propagate always** — Pass via HTTP header `X-Correlation-ID`, message metadata, or function parameter
3. **Log always** — Every log entry includes the correlation ID
4. **Preserve on errors** — Every `ErrorContext` includes the correlation ID

### 8.2 Implementation

```python
import uuid
from contextvars import ContextVar

# Thread-safe correlation ID storage
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    """Get current correlation ID, generate if missing."""
    cid = _correlation_id.get()
    if not cid:
        cid = f"req-{uuid.uuid4().hex[:12]}"
        _correlation_id.set(cid)
    return cid
```

---

## 9. Forbidden Patterns

| Pattern | Why Forbidden | Alternative |
|:--------|:-------------|:------------|
| `except: pass` | Swallows ALL errors silently | Catch specific, log, handle |
| `except Exception: pass` | Hides bugs | Catch specific types |
| `except Exception as e: print(e)` | No stack trace, no context | Use `logger.exception()` |
| Returning `None` on error | Caller doesn't know it failed | Raise or return Result type |
| `catch (e) { /* empty */ }` | JS/TS equivalent of swallowing | Log and handle |
| Logging without stack trace | Useless for debugging | Always include `traceback` |
| Catching too broadly at low level | Prevents proper propagation | Catch at the right layer |

---

## 10. Async & Background Task Safety

Background tasks are the #1 source of silent failures. They run outside the normal call stack and their errors vanish unless explicitly caught.

### 10.1 Python asyncio

```python
async def safe_task(coro, name: str) -> None:
    """Wrapper that ensures background task errors are never lost."""
    try:
        await coro
    except asyncio.CancelledError:
        logger.info(f"Task '{name}' cancelled")
        raise
    except Exception:
        logger.exception(f"Task '{name}' crashed — writing crash artifact")
        write_crash_artifact(*sys.exc_info())
        raise

# ✅ GOOD: Use the wrapper
task = asyncio.create_task(safe_task(my_coroutine(), "data_sync"))

# ❌ BAD: Bare create_task — errors vanish silently
task = asyncio.create_task(my_coroutine())
```

### 10.2 JavaScript Promises

```typescript
// ✅ GOOD: Always attach error handler
someAsyncOperation()
  .catch((error) => {
    logger.error('Background operation failed', { error, stack: error.stack });
  });

// ❌ BAD: Fire and forget
someAsyncOperation();  // If this rejects, the error is lost
```

---

## 11. Failure Mode & Effects Analysis (NASA-HDBK-2203 §4.4)

Before deploying any system with error handling, conduct a **Failure Mode & Effects Analysis (FMEA)** to systematically identify what can fail, how it fails, and what happens when it does.

### 11.1 FMEA Requirements

For each component/service, document:

| Column | Description |
|:-------|:------------|
| **Failure Mode** | What can go wrong (e.g., "database connection lost") |
| **Cause** | Why it would fail (e.g., "network partition", "OOM") |
| **Effect** | What happens to the system (e.g., "writes fail, reads serve stale cache") |
| **Severity** | Level 1–5 per §3 |
| **Detection** | How the failure is detected (e.g., "health check timeout", "error rate spike") |
| **Mitigation** | Recovery strategy per §7 |
| **Residual Risk** | What risk remains after mitigation |

### 11.2 When FMEA Is Required

- **Always** for safety-critical components (Severity 1–2)
- **Before first deployment** of any new service
- **After major architecture changes** that alter failure boundaries
- **Annually** as part of system review for long-running services

---

## 12. Post-Incident Review (NPR 7150.2D §3.8)

Every Severity 1–3 error that reaches production triggers a **mandatory post-incident review**.

### 12.1 Timeline

| Severity | Review Deadline | Report Due |
|:---------|:---------------|:-----------|
| **1 — CATASTROPHIC** | Within 24 hours | 48 hours |
| **2 — HAZARDOUS** | Within 48 hours | 1 week |
| **3 — MAJOR** | Within 1 sprint | End of sprint |

### 12.2 Post-Incident Report Template

```markdown
# Post-Incident Report: [ERROR_ID]

## Summary
- **Date/Time**: [ISO 8601]
- **Severity**: [1-5]
- **Duration**: [time to detection → time to resolution]
- **Impact**: [what was affected, how many users/requests]

## Timeline
- [HH:MM] Event detected via [detection method]
- [HH:MM] On-call notified
- [HH:MM] Root cause identified
- [HH:MM] Fix deployed
- [HH:MM] Confirmed resolved

## Root Cause Analysis
[5 Whys or Fishbone analysis]

## Corrective Actions
- [ ] [Action item with owner and due date]
- [ ] [Regression test added per GOV-002 §21]
- [ ] [FMEA updated if new failure mode discovered]

## Lessons Learned
[What we learned and what changes to prevent recurrence]
```

### 12.3 The Blameless Rule

Post-incident reviews are **blameless**. The goal is to improve the system, not assign fault. Focus on: *What conditions allowed this to happen? How do we prevent it?*

---

## 13. Compliance Checklist

Before deploying any service:

- [ ] Global exception handler installed at every entry point (§4)
- [ ] All custom exceptions extend `ApplicationError` with structured context (§4)
- [ ] All errors include full stack traces in logs (Law #2)
- [ ] Severity levels assigned per §3 taxonomy
- [ ] Correlation IDs generated at ingress and propagated everywhere (§8)
- [ ] All background/async tasks wrapped with error handlers (§10)
- [ ] Crash artifacts written for FATAL and unhandled errors (§6)
- [ ] No forbidden patterns present — `except: pass` scanner passes (§9)
- [ ] Recovery strategies match the error taxonomy (§7)
- [ ] Circuit breakers configured for external dependencies (§7.2)
- [ ] FMEA completed for all Severity 1-2 components (§11)
- [ ] Post-incident review process documented and team trained (§12)
- [ ] Error logs include: timestamp, error_id, severity, category, message, stack_trace, correlation_id
- [ ] Crash artifact destination defined in project specification (§6.2)

---

## 14. Agent Instructions

When an architect asks you to "set up error handling" or "add error handling," follow this protocol:

1. **Install global exception handler** at every entry point (§4)
2. **Create `ApplicationError` base class** with `ErrorContext` (§4)
3. **Define error categories** relevant to the project (§2)
4. **Assign severity levels** to each category (§3)
5. **Wrap all async/background tasks** with safe wrappers (§10)
6. **Set up crash artifact storage** per project specification (§6)
7. **Implement correlation ID propagation** (§8)
8. **Configure static scanner** to reject forbidden patterns (§9)
9. **Create FMEA** for all Severity 1-2 components (§11)
10. **Document post-incident review process** (§12)
11. **Add to CI pipeline** — scanner must pass before merge

---

> **"A silent crash is a lie. A logged crash is a lesson."**
