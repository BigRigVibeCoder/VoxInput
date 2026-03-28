---
id: BCK-001
title: "Governance Remediation Backlog"
type: planning
status: ACTIVE
owner: architect
agents: [architect]
tags: [project-management, backlog, governance, remediation]
related: [GOV-001, GOV-002, GOV-003, GOV-004]
created: 2026-03-28
updated: 2026-03-28
version: 1.0.0
---

> **BLUF:** This backlog tracks the systemic remediation of the VoxInput codebase to align with the core Agentic Architect standards. Specifically resolving Disaster Readability, Strict Typing, Error Catching bounds, and 1:1 Coverage mapping.

# Governance Remediation Backlog

## Work Categories

| Category | Code | Description |
|:---------|:-----|:------------|
| **Documentation** | REM-DOC | Disaster-Readability sweeps, Panic breadcrumbs (GOV-001) |
| **Typing** | REM-TYPE | Enforcing 100% type annotations (GOV-003) |
| **Logic Refactoring**| REM-REF | Breaking down methods >60 lines (GOV-003) |
| **Safety Bound** | REM-SAFE | Fail Loud patterns and exact exceptions (GOV-004) |
| **Audit Coverage** | REM-TEST | Establishing 1:1 test coverage mapping (GOV-002) |

---

## Task List

| ID | Task | Category | Dependencies | Deliverable | Status |
|:---|:-----|:---------|:-------------|:------------|:-------|
| B-001 | Disaster Readability Annotations in `main.py` | REM-DOC | None | `main.py` refactor | [ ] |
| B-002 | Extract sub-routines from `_ptt_finalize()` | REM-REF | None | `main.py` refactor | [ ] |
| B-003 | Full type hint coverage across core modules | REM-TYPE | None | Typing sweep | [ ] |
| B-004 | Eliminate raw Exception swallows | REM-SAFE | None | Error handler setup | [ ] |
| B-005 | 1:1 Coverage Map and Missing Test Stubs | REM-TEST | None | Test stubs + audit | [ ] |
| B-006 | Integration and E2E Test Scaffolding | REM-TEST | B-005 | Mock streams + Xvfb E2E | [ ] |
| B-007 | GOV-006 Trace Logging Instrumentation | REM-LOG | None | @trace_execution + codebase sweep | [x] |
