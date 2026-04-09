---
id: SPR-002
title: "Type Strictness & Fail-Loud Safety"
type: how-to
status: ARCHIVED
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, typing, safety]
related: [BCK-001, GOV-003, GOV-004]
created: 2026-03-28
updated: 2026-03-28
version: 1.0.0
---

> **BLUF:** Sprint 002 implements Python 3.10 type inference on all functions to adhere to GOV-003 100% typing mandates. Simultaneously hardens the try/except blocks per GOV-004 to remove silent error swallowing.

# Sprint 002: Strict Typing & Errors

**Phase:** 1 - Foundation Hardening
**Target:** Scope-bounded (Source wide)
**Agent(s):** Backend Developer 
**Dependencies:** None
**Contracts:** None

---

## ⚠️ Mandatory Compliance — Every Task

> All tasks in this sprint MUST incorporate these governance standards. They are not optional and not deferred.

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-003** | Python 3.10+ typing syntax. Target 100% type coverage on method signatures. |
| **GOV-004** | Use discrete Exception catching. Never swallow exceptions with `pass`. |
| **GOV-005** | Branch: `feature/SPR-002-typing-safety`. |
| **GOV-007** | Task status updated. |

---

## Developer Tasks

### T-001: 100% Signature Typing
- **Branch:** `feature/SPR-002-typing-safety`
- **Dependencies:** None
- **Deliverable:**
  - Audit all `def` signatures in `main.py`, `ui.py`, and `audio.py`.
  - Apply accurate parameters and return types (e.g. `-> None`).
- **Status:** [x] Complete

### T-002: Remediation of Bare Swallows
- **Branch:** `feature/SPR-002-typing-safety`
- **Dependencies:** None
- **Deliverable:**
  - Locate `except Exception:` hooks in `main.py` (specifically around PTT input logic).
  - Explicitly log them using the `structlog` logger. Replace `pass` instances with `logger.error("Context: %s", e)`.
- **Status:** [x] Complete

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 | Developer | [x] | `feature/SPR-002-typing-safety` | [x] |
| T-002 | Developer | [x] | `feature/SPR-002-typing-safety` | [x] |

---

## Sprint Completion Criteria

- [x] All tasks pass acceptance criteria
- [x] `mypy src/` passes with improved coverage thresholds.
- [x] No bare `pass` operations inside `except Exception:` scopes remaining in core modules.
