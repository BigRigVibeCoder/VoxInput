---
id: SPR-004
title: "NASA-Grade Error Taxonomy & Excepthook"
type: how-to
status: COMPLETE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, errors, safety]
related: [BCK-001, GOV-004]
created: 2026-03-28
updated: 2026-03-28
version: 1.0.0
---

> **BLUF:** Sprint 004 enforces the exact "zero-dark-failure" GOV-004 protocol. Replaces raw `Exceptions` with an `ApplicationError` domain hierarchy and intercepts raw GUI crashes.

# Sprint 004: NASA-Grade Error Taxonomy

**Phase:** 1 - Foundation Hardening
**Target:** Scope-bounded (Error Hierarchy)
**Agent(s):** Backend Developer 
**Dependencies:** SPR-002 (Type Strictness)
**Contracts:** None

---

## ⚠️ Mandatory Compliance — Every Task

> All tasks in this sprint MUST incorporate these governance standards. They are not optional and not deferred.

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-004** | Construct the explicit 13-category taxonomy (or relevant subset) as custom Python Exceptions. Tie to `sys.excepthook`. |
| **GOV-005** | Branch: `feature/SPR-004-error-taxonomy`. |
| **GOV-006** | All custom exceptions use structured PINO-equivalent `structlog` formatting upon failure. |

---

## Developer Tasks

### T-001: ApplicationError Core Taxonomy
- **Branch:** `feature/SPR-004-error-taxonomy`
- **Dependencies:** None
- **Deliverable:**
  - Create `src/errors.py`.
  - Stub a base `ApplicationError` with payload formatting.
  - Subclass at minimum: `AudioIOError`, `EngineCrashError`, and `InjectionFallbackError` representing the environment defined in GOV-008.
- **Status:** [x] Complete

### T-002: Excepthook Override (Fatal Trapping)
- **Branch:** `feature/SPR-004-error-taxonomy`
- **Dependencies:** T-001
- **Deliverable:**
  - In `src/main.py` entrypoint, override `sys.excepthook` to ensure uncaught desktop GUI exceptions log context to the SQLite black box before termination.
- **Status:** [x] Complete

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 | Developer | [x] | `feature/SPR-004-error-taxonomy` | [x] |
| T-002 | Developer | [x] | `feature/SPR-004-error-taxonomy` | [x] |
