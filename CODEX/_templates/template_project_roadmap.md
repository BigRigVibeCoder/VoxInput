---
id: PRJ-NNN
title: "[Project Name] — Roadmap"
type: explanation
status: DRAFT
owner: human
agents: [all]
tags: [project-management, roadmap, governance, agentic-development]
related: [BCK-001]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** [Project name] is [one sentence description]. The goal is [outcome]. This roadmap defines the vision, phased delivery plan, and success criteria that all agents work toward.

# [Project Name] — Project Roadmap

> **This document is authored by the Human. The Architect Agent maintains it.**

---

## 1. Project Vision

[2–3 paragraphs. What problem does this project solve? Who benefits? What does success look like in concrete terms?]

---

## 2. Guiding Principles

[3–5 bullet points. What values and constraints shape all decisions on this project?]

- **[Principle 1]:** [Brief explanation]
- **[Principle 2]:** [Brief explanation]
- **[Principle 3]:** [Brief explanation]

---

## 3. Scope

### 3.1 In Scope
- [What this project explicitly covers]

### 3.2 Out of Scope
- [What this project explicitly does NOT cover — prevents scope creep]

---

## 4. Delivery Phases

Phases are **scope-bounded**, not time-bounded. Each phase is complete when its exit criteria are met.

### Phase 1: [Name]
**Goal:** [One sentence]
**Exit criteria:**
- [ ] [Concrete, testable criterion]
- [ ] [Concrete, testable criterion]

**Key deliverables:**
- `BLU-NNN` — [Blueprint title]
- `CON-NNN` — [Contract title]
- `SPR-NNN` — [Sprint title]

---

### Phase 2: [Name]
**Goal:** [One sentence]
**Exit criteria:**
- [ ] [Criterion]

**Key deliverables:**
- [As above]

---

## 5. Agent Team

| Role | Agent Type | Primary CODEX Docs |
|:-----|:-----------|:------------------|
| Project manager | Architect Agent | `AGT-001`, all `SPR-`, all `CON-` |
| Implementation | Developer Agent(s) | `AGT-002`, assigned `SPR-` |
| Quality | Tester Agent | `AGT-003`, `VER-`, `40_VERIFICATION/` |

---

## 6. Key Contracts

List the binding interface contracts for this project:

| Contract | Description | Status |
|:---------|:------------|:-------|
| `CON-NNN` | [Interface name] | `DRAFT` |

---

## 7. Success Criteria

This project is complete when:
- [ ] All phases completed and archived
- [ ] All contracts at `STABLE` status
- [ ] All `DEF-` defects resolved or explicitly deferred
- [ ] Human signs off on final verification report

---

## 8. Change Log

| Date | Version | Change | Author |
|:-----|:--------|:-------|:-------|
| YYYY-MM-DD | 1.0.0 | Initial roadmap | Human |
