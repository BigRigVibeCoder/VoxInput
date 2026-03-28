---
id: VER-001
title: "Sprint Audit Checklist"
type: reference
status: DRAFT
owner: architect
agents: [architect]
tags: [verification, audit, testing, governance, sprint]
related: [GOV-002, GOV-007]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** Reusable checklist the Architect runs after every sprint. Clone this template, fill in the sprint ID, and check every box before marking the sprint CLOSED. Any failure → DEF- report filed.

# VER-001: Sprint Audit Checklist

**Sprint under audit:** `SPR-NNN`
**Agent(s):** `[Frontend / Backend / Both]`
**Audit date:** `YYYY-MM-DD`

---

## 1. Build Verification

| Check | Repo | Status |
|:------|:-----|:-------|
| `npm install` succeeds | [repo] | [ ] |
| `npm run build` succeeds (production) | [repo] | [ ] |
| `npm run lint` passes | [repo] | [ ] |
| `npm run typecheck` passes (if TS) | [repo] | [ ] |
| `npm run test` passes | [repo] | [ ] |

---

## 2. Health & Integration

| Check | Status |
|:------|:-------|
| Health endpoint returns 200 | [ ] |
| Service starts on correct port | [ ] |
| CODEX submodule is linked and current | [ ] |
| `.env.example` has all required vars | [ ] |

---

## 3. Governance Compliance

| GOV Doc | Requirement | Status |
|:--------|:------------|:-------|
| **GOV-001** | README present. TSDoc/JSDoc on exported functions. | [ ] |
| **GOV-002** | Test infrastructure configured. Tests exist and pass. Coverage ≥ thresholds. | [ ] |
| **GOV-003** | TypeScript strict mode. No `any` types. ESLint configured. Complexity ≤ 10. | [ ] |
| **GOV-004** | Error middleware present. Structured error responses. No unhandled rejections. | [ ] |
| **GOV-005** | Branch naming correct. Commit message format correct. | [ ] |
| **GOV-006** | Structured JSON logging configured. Correlation IDs present. | [ ] |
| **GOV-008** | Correct port. Correct database. `.env.example` matches GOV-008. | [ ] |

---

## 4. Contract Compliance (if applicable)

| Contract | Check | Status |
|:---------|:------|:-------|
| `CON-NNN` | Routes match contract schemas exactly | [ ] |
| `CON-NNN` | Error codes match contract | [ ] |
| `CON-NNN` | Auth mechanism matches contract | [ ] |

---

## 5. Sprint Task Verification

| Task | Acceptance Criteria Met | Status |
|:-----|:------------------------|:-------|
| T-NNN | [criteria from sprint doc] | [ ] |

---

## 6. Audit Verdict

| Field | Value |
|:------|:------|
| **Verdict** | `PASS / FAIL` |
| **Failures** | [list DEF- IDs filed, or "None"] |
| **Deploy approved** | `YES / NO / CONDITIONAL` |
| **Notes** | [any observations] |
