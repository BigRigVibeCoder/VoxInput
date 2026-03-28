---
id: GOV-003
title: "Coding Standard"
type: reference
status: APPROVED
owner: architect
agents: [all]
tags: [coding, standards, governance, quality, safety]
related: [GOV-001, GOV-002]
created: 2026-03-04
updated: 2026-03-05
version: 2.2.0
---

> **BLUF:** NASA/JPL-grade polyglot coding standard for agent-written code. Covers Python, C/C++, and React/TypeScript. Enforces NASA Power of 10, MISRA C:2025, DO-178C code review mandates, dead code prohibition, boundary condition requirements, incident-readability enhancements (inline ADRs, panic breadcrumbs, contract/failure-mode annotations), WCAG 2.1 AA accessibility, deterministic testability (`data-testid`), and the Disaster-Readability Principle. While 99% of this code will never be read by humans, it MUST be written so that in a disaster, a human engineer can understand any function in 30 seconds.

# Coding Standard: The Engineering Discipline

> **"Simple, Verifiable, Obvious."**
> *— JPL Institutional Coding Standard (D-17698)*

---

## 1. The Disaster-Readability Principle

> **"Code written by agents, readable by humans under stress."**

Most code in this system will be written, reviewed, and maintained by AI agents. But when things go catastrophically wrong — production outage at 3 AM, data corruption, security breach — **a human** will be dropped into the codebase cold. That human will be stressed, sleep-deprived, and unfamiliar with the code.

**Every line of code must be written as if a panicked engineer is reading it for the first time.**

### 1.1 The 30-Second Rule

Any function must be understandable by a competent engineer in **30 seconds** without:
- Reading external documentation
- Understanding the broader architecture
- Running the code

### 1.2 Mandatory Commenting Strategy

| Comment Type | When Required | Purpose |
|:-------------|:--------------|:--------|
| **File header** | Every file | Context: what this file does, who uses it |
| **Function docstring** | Every public function | What it does, what it takes, what it returns |
| **"Why" comments** | Any non-obvious logic | Explain the *reason*, not the *mechanism* |
| **Safety comments** | Any safety-critical code | Explain what happens if this fails |
| **TODO/FIXME/HACK** | Temporary workarounds | Must include author and date |
| **Invariant assertions** | Complex algorithms | What must be true at this point |
| **Decision Record** | Any non-trivial design choice | Inline mini-ADR: what was chosen, alternatives, and tradeoff |
| **Reading Guide / Panic Breadcrumbs** | Complex modules (≥3 public functions) | Ordered triage guide for incident responders |
| **Contract comments** | Functions with preconditions, side effects, or thread constraints | Preconditions, postconditions, side effects, thread safety |
| **Failure Mode annotations** | Any function whose failure affects downstream consumers | Blast radius, mitigation, and fallback behavior |
| **Cross-Reference anchors** | Code tied to specs, tickets, or related code | `REF:`, `SEE ALSO:` links to CODEX docs, defects, or sibling modules |

```python
# ❌ BAD: Comment restates the code
x = x + 1  # Increment x by 1

# ✅ GOOD: Comment explains WHY
x = x + 1  # Compensate for zero-indexed sensor array (firmware bug #42)

# ✅ GOOD: Safety comment
if distance_m < SAFE_STOP_DISTANCE_M:
    # SAFETY: If we don't stop here, the robot WILL collide.
    # Failure mode: physical damage, mission abort.
    emergency_stop()
```

### 1.3 Self-Documenting Structure

- **Small functions**: Maximum 60 lines. If you can't see the whole function without scrolling, split it.
- **Descriptive names**: `calculate_braking_distance_m()` not `calc_dist()`.
- **Guard clauses first**: Error paths at the top, happy path at the bottom.
- **One responsibility**: Each function does ONE thing.

### 1.4 Incident-Readability Enhancements

These comment types go beyond the basics. They ensure a human dropped cold into the codebase during an incident has **zero ambiguity** about what the code does, why it was written this way, and what breaks if it fails.

#### 1.4.1 Decision Record Comments (Inline ADR)

For any non-trivial design choice, embed a mini Architecture Decision Record directly in the code. This answers the inevitable *"but why didn't they just...?"* question.

```python
# DECISION: We use NumPy vectorization instead of a per-entity loop.
# ALTERNATIVES CONSIDERED: Pandas (too slow for >10k entities), Cython (build complexity).
# TRADEOFF: Readability is lower, but 50x performance gain is required for real-time.
# REF: BLU-002 §4.3 (performance requirements)
```

#### 1.4.2 Reading Guide / Panic Breadcrumbs

At the top of complex modules (≥3 public functions or ≥150 lines), add a **triage guide** that tells a panicked human where to start looking:

```python
"""
READING GUIDE FOR INCIDENT RESPONDERS:
1. If species are dying unexpectedly   → check _apply_mortality() and MORTALITY_THRESHOLD
2. If performance is degraded          → check _vectorized_step() batch sizes
3. If the RL agent is misbehaving      → check step() reward calculation
4. If state is corrupt after restart   → check reset() and _initialize_grid()
"""
```

#### 1.4.3 Contract Comments

Beyond standard docstrings, explicitly state **preconditions, postconditions, side effects, and thread safety** for functions that have them:

```python
def transfer_energy(source: Entity, target: Entity, amount_j: float) -> None:
    """Transfer energy between entities.

    PRECONDITION:  source.energy_j >= amount_j (caller must verify).
    POSTCONDITION: source.energy_j + target.energy_j == original_total (conservation law).
    SIDE EFFECTS:  Mutates both source and target in-place.
    THREAD SAFETY: Not thread-safe. Caller must hold simulation lock.
    """
```

#### 1.4.4 Failure Mode Annotations

For any function whose failure affects downstream consumers, document the **blast radius** and **mitigation**:

```python
# FAILURE MODE: If this returns None, the entire tick is skipped.
# BLAST RADIUS: All downstream consumers (renderer, RL agent) see stale state.
# MITIGATION: Caller retries once, then falls back to last-known-good state.
# SEE ALSO: GOV-004 §7.1 (recovery strategies)
```

#### 1.4.5 Cross-Reference Anchors

Link code to specs, tickets, and sibling modules. Use standard prefixes for machine-parseability:

```python
# REF: GOV-004 §3.2 (error escalation pattern)
# REF: DEF-017 (this workaround compensates for the sensor drift bug)
# SEE ALSO: engine/weather.py:_apply_temperature() — uses the same energy model
```

| Prefix | Meaning | Example |
|:-------|:--------|:--------|
| `REF:` | This code implements or is constrained by the referenced item | `REF: BLU-002 §4` |
| `SEE ALSO:` | Related code or docs that share logic or context | `SEE ALSO: utils/math.py:clamp()` |
| `DECISION:` | Opens an inline ADR block | `DECISION: Use SQLite over PostgreSQL` |
| `FAILURE MODE:` | Opens a failure annotation block | `FAILURE MODE: Returns empty list on timeout` |

---

## 2. The Power of 10 (Universal Rules)

> **Origin:** Gerard J. Holzmann, NASA/JPL Laboratory for Reliable Software, 2006

These rules apply to **ALL languages**. Static analysis must enforce them.

| # | Rule | Rationale |
|:--|:-----|:----------|
| 1 | **Simple control flow** — No recursion. No deeply nested logic (max 4 levels). | Analyzable by humans and tools. |
| 2 | **Fixed loop bounds** — All loops must have provable termination. | Prevents hangs in production. |
| 3 | **No dynamic allocation in hot loops** — Pre-allocate, reuse. | Prevents GC pauses and memory fragmentation. |
| 4 | **Short functions** — Max 60 lines per function/method. | Fits on one screen = one mental model. |
| 5 | **Assertion density** — Min 2 assertions per non-trivial function. | Internal correctness proofs. |
| 6 | **Minimal data scope** — No module-level mutable state. Smallest scope possible. | Prevents spooky action at a distance. |
| 7 | **Check all return values** — Never ignore results from fallible operations. | Prevents silent failures. |
| 8 | **Pedantic warnings** — All linter/compiler warnings treated as errors. Zero tolerance. | Catches bugs that humans miss. |

---

## 3. Naming Conventions (All Languages)

Names must convey **intent**, **type**, and **scope** without reading the implementation.

### 3.1 Universal Patterns

| Pattern | Use Case | Examples |
|:--------|:---------|:---------|
| `verb_noun` | Functions/methods | `calculate_distance`, `validate_input`, `fetchUserData` |
| `noun_unit` | Physical quantities | `distance_m`, `velocity_mps`, `timeout_ms` |
| `is_`, `has_`, `can_` | Booleans | `is_active`, `has_permission`, `canSubmit` |
| `max_`, `min_`, `default_` | Limits/defaults | `MAX_RETRIES`, `min_temperature_c` |
| `UPPER_SNAKE_CASE` | Constants | `MAX_VELOCITY_MPS`, `API_ENDPOINT` |

### 3.2 Language-Specific Casing

| Element | Python | C/C++ | TypeScript/React |
|:--------|:-------|:------|:-----------------|
| Variables | `snake_case` | `snake_case` | `camelCase` |
| Functions | `snake_case` | `snake_case` | `camelCase` |
| Classes/Components | `PascalCase` | `PascalCase` | `PascalCase` |
| Constants | `UPPER_SNAKE` | `UPPER_SNAKE` | `UPPER_SNAKE` |
| Files | `snake_case.py` | `snake_case.c` | `PascalCase.tsx` or `kebab-case.ts` |
| Private members | `_prefix` | `m_prefix` or `_prefix` | `_prefix` or `#private` |

### 3.3 Forbidden Naming

- ❌ Single-letter variables (except `i`, `j`, `k` in loops, `e` in exceptions)
- ❌ Abbreviations unless universally understood (`cfg` → `config`, `mgr` → `manager`)
- ❌ Generic names: `data`, `info`, `temp`, `result`, `value`, `item` — add context

---

## 4. File Structure & Organization

### 4.1 File Size Limits

| Metric | Limit | Enforcement |
|:-------|:------|:------------|
| Lines per file | ≤300 (target), ≤500 (absolute max) | Linter |
| Lines per function | ≤60 | Linter |
| Cyclomatic complexity | ≤10 per function | Linter |
| Nesting depth | ≤4 levels | Linter |
| Parameters per function | ≤5 (use config objects beyond) | Code review |

### 4.2 Universal File Layout

Every source file follows this order:

```
1. File header comment / module docstring
2. Imports (Standard → Third-party → Local)
3. Constants
4. Type definitions / Interfaces
5. Module-level logger (if applicable)
6. Classes / Functions (public first, private last)
7. Entry point (if applicable)
```

---

## 5. Defensive Coding (All Languages)

### 5.1 Input Validation

All public function inputs **MUST** be validated. Do not trust callers — even other agents.

### 5.2 Guard Clauses First

Handle error conditions at the top of the function, then the happy path:

```python
def process(data: InputData) -> Result:
    if data is None:
        raise ValueError("data cannot be None")
    if not data.is_valid():
        raise ValidationError(f"Invalid data: {data}")
    
    # Happy path starts here
    return transform(data)
```

### 5.3 No Magic Numbers

All numeric literals **MUST** be named constants. The name explains the value.

```python
# ❌ BAD — What is 0.3? Why 0.3?
if distance < 0.3:
    stop()

# ✅ GOOD — Self-documenting
SAFE_STOP_DISTANCE_M = 0.3  # Minimum distance before collision risk
if distance < SAFE_STOP_DISTANCE_M:
    stop()
```

### 5.4 Boundary Condition Handling (NASA-HDBK-2203 §5.3)

Every function that accepts ranges, collections, or external input **MUST** explicitly handle boundary conditions:

- **Empty inputs** — empty collections, zero-length strings, null/None
- **Off-by-one** — first element, last element, length ± 1
- **Overflow/underflow** — integer limits, float precision, buffer sizes
- **Negative values** — when only positive is valid
- **Maximum size** — largest input the function can handle

```python
def get_element(items: list[T], index: int) -> T:
    # BOUNDARY: empty collection
    if not items:
        raise ValueError("Cannot get element from empty list")
    # BOUNDARY: negative index
    if index < 0:
        raise IndexError(f"Negative index not allowed: {index}")
    # BOUNDARY: overflow
    if index >= len(items):
        raise IndexError(f"Index {index} out of range [0, {len(items) - 1}]")
    return items[index]
```

### 5.5 Forbidden Patterns (All Languages)

| Pattern | Why | Alternative |
|:--------|:----|:------------|
| Bare `catch`/`except` | Swallows all errors | Catch specific types |
| `eval()` / `exec()` | Code injection | Structured data |
| Module-level mutable state | Unpredictable | Encapsulate in classes |
| Wildcard imports | Namespace pollution | Import specific names |
| Mutable default arguments | Shared state | Use `None` sentinel |
| Ignoring return values | Silent failures | Always check or comment `_ =` |
| **Dead code** | Confuses readers, hides bugs | Delete it. Use VCS to retrieve. |
| **Unreachable code** | Indicates logic errors | Remove or fix control flow |
| **Commented-out code** | Not documentation, just noise | Delete it. Git remembers. |

---

## 6. Python-Specific Standards

> Primary language. NASA Power of 10 fully adapted.

### 6.1 Type Hinting (100% Coverage)

- 100% of function signatures must be typed
- Use Python 3.10+ syntax: `str | None` over `Optional[str]`
- Forbidden: `Any` (except JSON boundaries), `object`, untyped `lambda`
- Use semantic types: `Meters = float`, `Seconds = float`

### 6.2 Docstrings (Google Style)

```python
def calculate_distance(
    origin: tuple[float, float],
    target: tuple[float, float],
) -> float:
    """Calculate Euclidean distance between two 2D points.

    Uses the standard distance formula. This is called by the
    navigation planner to evaluate waypoint proximity.

    Args:
        origin: Starting point as (x, y) in meters.
        target: Destination point as (x, y) in meters.

    Returns:
        Distance in meters between the two points.

    Raises:
        ValueError: If either point contains NaN values.
    """
```

### 6.3 Import Order

```python
"""Module docstring."""

# 1. Standard library
import os
from pathlib import Path

# 2. Third-party
import structlog
from pydantic import BaseModel

# 3. Local application
from myproject.models import Config
from myproject.utils import validate

# 4. Constants
MAX_RETRIES = 3
logger = structlog.get_logger(__name__)
```

### 6.4 Concurrency (GIL Awareness)

- **CPU-bound**: Use `multiprocessing` or C extensions
- **I/O-bound**: Use `asyncio`
- **Never** use threads for CPU work (GIL blocks parallelism)
- **Never** block the event loop with CPU work — offload via `run_in_executor`

### 6.5 Tools & Enforcement

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| Ruff | Linting + formatting | Zero warnings |
| MyPy `--strict` | Type checking | Zero errors |
| Radon | Cyclomatic complexity | No function > 10 |
| Bandit | Security scanning | Zero HIGH/CRITICAL |

---

## 7. C/C++ Standards

> For performance-critical components, embedded systems, and system-level code.

### 7.1 Compliance Targets

| Standard | When |
|:---------|:-----|
| **MISRA C:2025** | All C code — safety-critical subset |
| **CERT C** | Security-focused modules |
| **C17 or later** | Minimum language standard |
| **C++17 or C++20** | Minimum for C++ |

### 7.2 Key Rules (Beyond Power of 10)

- **No dynamic memory after init** — `malloc`/`free` forbidden after startup. Pre-allocate all buffers.
- **No recursion** — Stack overflow is fatal in embedded. Use iteration.
- **Single level of indirection** — `*ptr` is fine. `**ptr` requires justification.
- **All variables initialized at declaration** — Uninitialized memory is undefined behavior.
- **No `goto`** — Exception: single-point-of-return cleanup pattern in C is acceptable:

```c
int process(data_t *data) {
    int result = -1;
    buffer_t *buf = NULL;
    
    if (data == NULL) goto cleanup;
    
    buf = buffer_alloc(1024);
    if (buf == NULL) goto cleanup;
    
    /* SAFETY: buf is guaranteed allocated here */
    result = transform(data, buf);
    
cleanup:
    buffer_free(buf);  /* Safe: buffer_free(NULL) is a no-op */
    return result;
}
```

### 7.3 Header File Discipline

```c
/**
 * @file motor_controller.h
 * @brief Motor control interface for the drive system.
 * 
 * Provides velocity commands and safety limit enforcement.
 * Used by: arbiter, reflex engine.
 * 
 * SAFETY: All velocity commands are hard-clamped by MAX_VELOCITY_MPS.
 */

#ifndef MOTOR_CONTROLLER_H
#define MOTOR_CONTROLLER_H

#include <stdint.h>
#include <stdbool.h>

/** Maximum allowable velocity in meters per second. */
#define MAX_VELOCITY_MPS  (1.5)

/**
 * Set the target velocity for the drive motors.
 * 
 * @param velocity_mps  Target velocity in m/s. Clamped to [-MAX, +MAX].
 * @return 0 on success, -1 on hardware fault.
 * 
 * SAFETY: Returns -1 and stops motors if velocity exceeds physical limits.
 */
int motor_set_velocity(double velocity_mps);

#endif /* MOTOR_CONTROLLER_H */
```

### 7.4 Tools & Enforcement

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| `gcc -Wall -Wextra -Werror -pedantic` | All warnings as errors | Zero warnings |
| `clang-tidy` | Static analysis | Zero findings |
| `cppcheck` | Additional static analysis | Zero HIGH |
| MISRA checker (PC-lint, Polyspace) | MISRA compliance | If safety-critical |
| `valgrind` | Memory error detection | Zero errors |
| `AddressSanitizer` | Runtime memory safety | Clean runs |

---

## 8. React / TypeScript Standards

> For web interfaces, dashboards, and user-facing applications.

### 8.1 TypeScript Configuration

```json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

### 8.2 Component Standards

- **Functional components only** — no class components
- **Max ~150 lines per component** — split if larger
- **Props use `interface`** — state/hooks use `type`
- **One component per file**
- **Early returns** for loading/error states before the main render
- **Semantic HTML elements** — use `<article>`, `<section>`, `<nav>` over generic `<div>` for top-level wrappers
- **Design-decision comments** — explain *why*, not *what*, especially on guard clauses and fallback values

```tsx
/**
 * Renders a single dashboard metric card with optional trend indicator.
 *
 * **Design decisions:**
 * - Guard clause exits early for `loading` state (GOV-003 §5.2).
 * - Null-safe fallback for `value` prevents blank cards in edge cases.
 * - Semantic `<article>` with `aria-label` enables screen-reader navigation.
 * - `data-testid` attributes allow deterministic test selectors.
 *
 * Used by: Dashboard, AdminPanel
 *
 * DISASTER NOTE: If this component fails to render, the operator
 * loses visibility into system health. Fail-safe: raw JSON fallback.
 *
 * @example
 * ```tsx
 * <KPICard
 *     title="Monthly Revenue"
 *     value="$124,500"
 *     icon={DollarSign}
 *     trend={{ value: 8.1, label: 'vs last month' }}
 * />
 * ```
 */
interface KPICardProps {
  /** Human-readable title displayed at the top of the card */
  title: string;
  /** Formatted display value (e.g., "$124,500") */
  value: string | null;
  /** Lucide icon component */
  icon: React.ComponentType;
  /** Optional trend data with percentage and label */
  trend?: TrendData;
  /** Whether the card is in a loading state */
  loading?: boolean;
}

export default function KPICard({ title, value, icon: Icon, trend, loading = false }: KPICardProps) {
  /* Guard: Loading state (GOV-003 §5.2 — early return) */
  if (loading) {
    return <div role="status" aria-label={`Loading ${title}`} data-testid="kpi-skeleton">...</div>
  }

  /** Defensive fallback: prevents blank cards if upstream data is missing. */
  const safeValue = value ?? MISSING_VALUE_PLACEHOLDER

  return (
    <article aria-label={`${title}: ${safeValue}`} data-testid={`kpi-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <Icon aria-hidden="true" />
      <span>{safeValue}</span>
    </article>
  )
}
```

### 8.3 Accessibility (WCAG 2.1 AA)

All UI components **MUST** include accessibility attributes:

| Requirement | Implementation | When Required |
|:------------|:---------------|:--------------|
| **`aria-label`** on containers | Describe the widget's content for screen readers | Every interactive or data-display component |
| **`aria-hidden="true"`** on decorative elements | Icons, gradient accents, visual flourishes | Every non-semantic visual element |
| **`role="status"`** on loading skeletons | Announce loading state to assistive technology | Every loading/skeleton state |
| **Semantic HTML** | `<article>` for cards, `<nav>` for navigation, `<section>` for page regions | Always prefer over `<div>` |
| **Color contrast** | All text meets 4.5:1 contrast ratio | Every text element |

```tsx
// ✅ GOOD — Accessible card with semantic HTML and ARIA
<article aria-label={`${title}: ${safeValue}`}>
    <div aria-hidden="true" className="decorative-gradient" />
    <Icon aria-hidden="true" />
</article>

// ❌ BAD — Generic div, no ARIA, icons announced by screen readers
<div>
    <Icon />
</div>
```

### 8.4 Testability (`data-testid` Attributes)

All components **MUST** include `data-testid` attributes for deterministic test selectors:

| Rule | Rationale |
|:-----|:----------|
| **Every rendered component root** gets a `data-testid` | Tests must not rely on CSS classes or text content |
| **Dynamic IDs** use kebab-case derived from props | `data-testid={\`kpi-card-${title.toLowerCase().replace(/\s+/g, '-')}\`}` |
| **Conditional sub-elements** get their own `data-testid` | `data-testid="kpi-trend"`, `data-testid="kpi-skeleton"` |
| **Never use `data-testid` for styling** | Test hooks are invisible to users |

### 8.5 Constants & Type Safety

All constant maps and enumerations **MUST** use `as const` assertions for maximum type narrowing:

```tsx
// ✅ GOOD — Type-safe, auto-complete friendly, immutable
const TREND_ARROW = { up: '↑', down: '↓' } as const
const TREND_COLORS = {
    positive: 'text-emerald-400',
    negative: 'text-rose-400',
} as const

// ❌ BAD — Mutable, widened to `string`, no auto-complete
const TREND_ARROW = { up: '↑', down: '↓' }
```

**Sub-interfaces**: When a prop contains a composite shape (e.g., `trend: { value, label }`), extract it into a **named interface** with per-field JSDoc:

```tsx
// ✅ GOOD — Self-documenting, reusable, hover-documented in IDE
interface TrendData {
    /** Percentage change vs previous period. Positive = green, negative = red. */
    value: number
    /** Contextual label displayed after the percentage (e.g., "vs last month"). */
    label: string
}

export interface KPICardProps {
    trend?: TrendData
}
```

### 8.6 JSDoc with `@example` Blocks

All exported components **MUST** include a JSDoc block with:

| Field | Required | Purpose |
|:------|:--------:|:--------|
| Summary line | ✅ | One sentence describing what the component renders |
| `**Design decisions:**` | ✅ | Bullet list of non-obvious architectural choices |
| `@example` block | ✅ | Copy-pasteable usage snippet |
| `Used by:` / `Related:` | ✅ | Consumer and standard references |

### 8.7 CSS Class Formatting

Tailwind utility classes **MUST** be split across multiple lines when they exceed 80 characters, grouped by concern:

```tsx
// ✅ GOOD — Grouped by concern: layout → color → animation
<article
    className="group relative overflow-hidden rounded-xl border border-zinc-800
               bg-zinc-950/40 p-6 shadow-sm shadow-black/20 backdrop-blur-xl
               transition-all duration-300
               hover:-translate-y-1 hover:border-zinc-700
               hover:bg-zinc-900/60 hover:shadow-md hover:shadow-white/5"
>

// ❌ BAD — Single unreadable line
<article className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/40 p-6 shadow-sm shadow-black/20 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-zinc-700 hover:bg-zinc-900/60 hover:shadow-md hover:shadow-white/5">
```

### 8.8 Naming Conventions

| Element | Convention | Example |
|:--------|:-----------|:--------|
| Components | `PascalCase` | `StatusPanel`, `UserProfile` |
| Hooks | `useCamelCase` | `useAuth`, `useSystemStatus` |
| Event handlers | `handleVerb` or `onVerb` | `handleSubmit`, `onClose` |
| Boolean props | `is/has/should` prefix | `isLoading`, `hasError` |
| Constants | `UPPER_SNAKE` | `MAX_RETRIES`, `API_URL` |
| Constant maps | `UPPER_SNAKE` + `as const` | `TREND_COLORS`, `STATUS_STYLES` |
| Utility files | `kebab-case.ts` | `date-utils.ts`, `api-client.ts` |

### 8.9 Tools & Enforcement

| Tool | Purpose | CI Gate |
|:-----|:--------|:--------|
| ESLint + TypeScript parser | Linting | Zero warnings |
| Prettier | Formatting | Pre-commit hook |
| `tsc --noEmit` | Type checking | Zero errors |

---

## 9. Error Handling Pattern (All Languages)

```
1. Validate inputs (guard clauses) → raise/return early
2. Execute the operation
3. Verify the output (post-condition assertions)
4. Handle failures explicitly — never silently swallow
5. Log the failure with full context
```

**The Golden Rules:**
- **Fail fast** — detect errors at the earliest possible point
- **Fail loud** — log with full context, never fail silently
- **Fail safe** — on unrecoverable error, enter a safe/degraded state
- **Fail traceable** — every error includes enough info to reproduce

---

## 10. Code Review Mandate (DO-178C §6.3.4)

> **All code must be peer-reviewed before merge.** No exceptions.

### 10.1 Review Requirements

| Code Type | Reviewer Requirement | Standard |
|:----------|:--------------------|:---------|
| Safety-critical | **Independent reviewer** (not the author) | DO-178C DAL-A |
| Core business logic | Peer review by any team member | DO-178C DAL-C |
| Utilities / non-critical | Self-review with checklist is acceptable | — |

### 10.2 What Reviewers Check

1. **Correctness** — Does the code do what the requirements specify?
2. **Boundary conditions** — Are all edge cases handled? (§5.4)
3. **Dead code** — Is there any unreachable or commented-out code? (§5.5)
4. **Naming** — Do names follow §3 conventions?
5. **Complexity** — Does any function exceed the metrics in §11?
6. **Error handling** — Does it follow GOV-004?
7. **Assertions** — Are there ≥2 per non-trivial function?
8. **30-second rule** — Can the reviewer understand each function in 30 seconds?

### 10.3 Agent Code Review

When agents write code, the reviewing agent (or human) MUST verify against this checklist. Agents writing safety-critical code MUST flag it for independent review with the comment `# SAFETY-CRITICAL: requires independent review`.

---

## 11. Compliance Metrics Dashboard

> Consolidated table of all quantitative thresholds. **One place to check, zero ambiguity.**

| Metric | Target | Absolute Limit | Enforcement | Source |
|:-------|:-------|:---------------|:------------|:-------|
| Lines per function | ≤40 | **≤60** | Linter | JPL D-60411 |
| Lines per file | ≤300 | **≤500** | Linter | JPL D-60411 |
| Cyclomatic complexity | ≤7 | **≤10** | Linter | McCabe / NIST |
| Nesting depth | ≤3 | **≤4** | Linter | JPL Power of 10 |
| Parameters per function | ≤4 | **≤5** | Code review | Clean Code |
| Assertion density | ≥2/function | **≥1/function** | Custom lint | JPL Rule 5 |
| Type coverage (Python) | 100% | **≥95%** | MyPy | JPL Rule 10 |
| Type coverage (TypeScript) | 100% | **≥95%** | tsc --strict | — |
| Dead code | 0 lines | **0 lines** | Linter | MISRA C:2025 |
| Compiler/linter warnings | 0 | **0** | CI gate | JPL Rule 10 |
| Code review coverage | 100% | **100%** | Process | DO-178C §6.3.4 |

---

## 12. Static Analysis Rule Profiles (JPL D-60411)

> Every project MUST specify which rule profile to enable. **No "we'll add linting later."**

### 12.1 Python — Ruff Profile

```toml
# pyproject.toml — Mandatory Ruff configuration
[tool.ruff]
select = ["ALL"]
ignore = [
    "D203",   # Conflicts with D211
    "D213",   # Conflicts with D212
    "COM812", # Conflicts with formatter
    "ISC001", # Conflicts with formatter
]
line-length = 120
target-version = "py310"

[tool.ruff.per-file-ignores]
"tests/**" = ["S101"]  # Allow assert in tests

[tool.ruff.pylint]
max-args = 5
max-statements = 50
```

### 12.2 C/C++ — Clang-Tidy Profile

```yaml
# .clang-tidy — Mandatory checks
Checks: >
  -*,
  bugprone-*,
  cert-*,
  clang-analyzer-*,
  misc-*,
  modernize-*,
  performance-*,
  readability-*,
  -modernize-use-trailing-return-type
WarningsAsErrors: '*'
HeaderFilterRegex: '.*'
```

### 12.3 TypeScript — ESLint Profile

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/strict-type-checked",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": "error",
    "no-console": "warn",
    "max-lines-per-function": ["warn", 60],
    "complexity": ["error", 10]
  }
}
```

### 12.4 NASA Power of 10 — Enforcement Matrix

> Which tool enforces which rule? **No rule without a scanner.**

| # | Power of 10 Rule | Python Enforcement | C/C++ Enforcement | TypeScript Enforcement |
|:--|:----------------|:-------------------|:-------------------|:-----------------------|
| 1 | Simple control flow (no goto) | Ruff `PLR5501` | Clang-Tidy `readability-avoid-goto` | ESLint `no-labels` |
| 2 | Fixed loop bounds (no unbounded loops) | Manual review + `@trace_execution` | MISRA C:2025 Rule 15.4 | Manual review |
| 3 | No dynamic alloc after init | Manual review | Clang-Tidy `cert-mem*` + MISRA | N/A (GC language) |
| 4 | Short functions (≤60 lines) | Ruff `PLR0915` | Clang-Tidy `readability-function-size` | ESLint `max-lines-per-function` |
| 5 | Assertion density (≥2/function) | Custom scanner + pytest | `assert` macro + Clang-Tidy | Custom ESLint rule |
| 6 | Minimal data scope (no globals) | Ruff `PLW0602`, `PLW0603` | Clang-Tidy `misc-use-anonymous-namespace` | ESLint `no-var` + strict |
| 7 | Check all return values | MyPy `--strict` + Ruff `RET` | Clang-Tidy `bugprone-unused-return-value` | `@typescript-eslint/no-unused-vars` |
| 8 | Limited preprocessor use | N/A | Clang-Tidy `modernize-macro-*` | N/A |
| 9 | Restrict pointer use | N/A | MISRA C:2025 Rules 18.* | N/A |
| 10 | Pedantic compilation (all warnings = errors) | Ruff `--select ALL` + MyPy strict | `-Wall -Werror -Wextra -pedantic` | `tsc --strict` |

**Agent Rule**: When setting up a project, verify that every applicable Power of 10 rule has an automated enforcer. If a tool doesn't exist for a rule, document the gap and require manual review.

---

## 13. Compliance Checklist

Before submitting code in **any language**:

- [ ] All functions ≤60 lines
- [ ] Cyclomatic complexity ≤10 per function
- [ ] Nesting depth ≤4 levels
- [ ] All public functions have docstrings/JSDoc/Doxygen comments
- [ ] All exported React components include `@example` JSDoc block (§8.6)
- [ ] All magic numbers replaced with named constants
- [ ] All constant maps use `as const` assertion (§8.5)
- [ ] All return values checked or explicitly ignored with comment
- [ ] Guard clauses handle error paths first
- [ ] ≥2 assertions per non-trivial function
- [ ] File header explains purpose and consumers
- [ ] No forbidden patterns (including dead code, unreachable code, commented-out code)
- [ ] All boundary conditions explicitly handled (§5.4)
- [ ] All linter/compiler warnings resolved (zero tolerance)
- [ ] Static analysis profile enabled and passing (§12)
- [ ] Code reviewed per §10 (independent review for safety-critical)
- [ ] A human can understand any function in 30 seconds
- [ ] Complex modules (≥3 public functions) have a Reading Guide / Panic Breadcrumbs (§1.4.2)
- [ ] Non-trivial design choices explained with Decision Record comments (§1.4.1)
- [ ] Functions with preconditions/side effects/thread constraints have Contract comments (§1.4.3)
- [ ] Functions with downstream impact have Failure Mode annotations (§1.4.4)
- [ ] Code tied to specs/tickets/sibling modules has Cross-Reference anchors (§1.4.5)
- [ ] **React/TS only:** Semantic HTML elements used (§8.3)
- [ ] **React/TS only:** ARIA attributes present on all components (§8.3)
- [ ] **React/TS only:** `data-testid` attributes on all component roots and key sub-elements (§8.4)
- [ ] **React/TS only:** Multi-line className formatting for long utility strings (§8.7)

---

> **"Code is read far more often than it is written. Write for the reader — especially the panicked one at 3 AM."**
