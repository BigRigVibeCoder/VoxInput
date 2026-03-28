---
id: SPR-NNN
title: "[Sprint Title]"
type: how-to
status: PLANNING
owner: architect
agents: [coder, tester]
tags: [project-management, sprint, workflow]
related: [BCK-001, BLU-NNN]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** Sprint [NNN] targets [goal in one sentence]. [N] tasks assigned to [Developer/Tester Agent]. Estimated completion: [timeframe or "scope-bounded"]. **Governance compliance is mandatory from task one.**

# Sprint [NNN]: [Title]

**Phase:** [Phase number and name]
**Target:** [timeframe] (AI-agent pace)
**Agent(s):** [Frontend / Backend / Both]
**Dependencies:** [Previous sprint(s) that must be complete]
**Contracts:** [CON-NNN — binding contracts for this sprint]

---

## ⚠️ Mandatory Compliance — Every Task

> All tasks in this sprint MUST incorporate these governance standards. They are not optional and not deferred.

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | [specific doc requirement for this sprint] |
| **GOV-002** | [specific testing requirement] |
| **GOV-003** | [specific coding standard requirement] |
| **GOV-004** | [specific error handling requirement] |
| **GOV-005** | Branch: `feature/SPR-NNN-description` (one per sprint). Commits: `feat(SPR-NNN): T-XXX description`. |
| **GOV-006** | [specific logging requirement] |
| **GOV-007** | Task status updated. Blockers → `DEF-` doc. |
| **GOV-008** | [specific infra requirement] |

**Acceptance gate:** No task is considered complete unless ALL applicable governance requirements are met.

---

## [Agent Name] Tasks

### T-NNN: [Task Title]
- **Branch:** `feature/SPR-NNN-TNNN-[short-description]`
- **Dependencies:** [T-NNN or None]
- **Contracts:** [CON-NNN §section or None]
- **Blueprints:** [BLU-NNN §section or None]
- **Deliverable:**
  - [Specific deliverable 1]
  - [Specific deliverable 2]
- **Acceptance criteria:**
  - [Specific, testable criterion 1]
  - [Specific, testable criterion 2]
- **Status:** [ ] Not Started

### T-NNN: [Next Task]
- **Branch:** `feature/SPR-NNN-TNNN-[short-description]`
- **Dependencies:** [T-NNN]
- **Deliverable:** [description]
- **Acceptance criteria:** [criteria]
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-NNN | [Agent] | [ ] | `feature/SPR-NNN-TNNN-description` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

- [ ] All tasks pass acceptance criteria
- [ ] All GOV compliance checks pass (Architect audit)
- [ ] All tests pass: `npm run lint && npm run typecheck && npm run test`
- [ ] Architect audit complete (VER-001 checklist)
- [ ] No open `DEF-` reports against this sprint

---

## Audit Notes (Architect)

[Architect fills this in during audit.]

**Verdict:** PASS / FAIL
**Deploy approved:** YES / NO
