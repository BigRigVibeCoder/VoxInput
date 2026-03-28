---
id: SPR-006
title: "GOV-006 Trace Logging Instrumentation"
type: how-to
status: IN_PROGRESS
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, logging, trace]
related: [BCK-001, GOV-006]
created: 2026-03-28
updated: 2026-03-28
version: 1.0.0
---

> **BLUF:** Sprint 006 instruments the VoxInput codebase with GOV-006 §8 trace logging. Adds the `@trace_execution` decorator, a `trace_logging` settings toggle, and TRACE-level calls across all 16 source modules.

# Sprint 006: GOV-006 Trace Logging Instrumentation

**Phase:** 2 - Observability & Forensics
**Target:** Codebase-wide (`src/`)
**Agent(s):** Backend Developer
**Dependencies:** None (logger.py infrastructure already exists)
**Contracts:** None

---

## ⚠️ Mandatory Compliance — Every Task

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-006** | All critical paths emit TRACE-level structured logs for agent reconstruction (§8). |
| **GOV-006** | `@trace_execution` decorator implemented per §5.3. |
| **GOV-005** | Branch: `feature/SPR-001-readability` (co-located with readability sweep). |

---

## Developer Tasks

### T-001: @trace_execution Decorator & Toggle
- **Deliverable:**
  - Implement `@trace_execution` in `src/logger.py` per GOV-006 §5.3.
  - Add `trace_logging_enabled()` and `set_trace_logging()` for runtime toggle.
  - On by default (TRACE level), user can disable via settings.
- **Status:** [x] Complete

### T-002: Core Module Instrumentation
- **Deliverable:**
  - `main.py`: model_load enter/exit, listening state changes, PTT merge results
  - `recognizer.py`: engine init, Vosk full results, word injection counts
  - `injection.py`: backend selection, dispatch, Unicode fallback decisions
  - `homophones.py`: transformation in→out logging
- **Status:** [x] Complete

### T-003: Peripheral Module Instrumentation
- **Deliverable:**
  - `audio.py`: stream start/stop
  - `settings.py`: load/save/change
  - `word_db.py`: init counts, reload
  - `c_ext/__init__.py`: C extension load vs numpy fallback decision
- **Status:** [x] Complete

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 | Developer | [x] | `feature/SPR-001-readability` | [ ] |
| T-002 | Developer | [x] | `feature/SPR-001-readability` | [ ] |
| T-003 | Developer | [x] | `feature/SPR-001-readability` | [ ] |
