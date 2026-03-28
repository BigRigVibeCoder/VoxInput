---
id: DEF-NNN
title: "[Short defect description]"
type: reference
status: DRAFT
owner: [agent-name]
agents: [coder, tester]
tags: [defect]
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** [One-sentence summary of the defect and its impact.]

# Defect Report: [Title]

## 1. Summary

| Field | Value |
|:------|:------|
| **Priority** | P0 / P1 / P2 / P3 |
| **Severity** | 1-CATASTROPHIC / 2-HAZARDOUS / 3-MAJOR / 4-MINOR / 5-NO EFFECT |
| **Status** | OPEN / IN-PROGRESS / FIXED / VERIFIED / CLOSED |
| **Discovered By** | [Agent name or Architect] |
| **Discovered During** | [Unit test / Integration test / E2E / UAT / Production] |
| **Component** | [Service or module affected] |
| **Branch** | `fix/DEF-NNN-short-description` |

## 2. Steps to Reproduce

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result**: [What should happen]
**Actual Result**: [What actually happens]

## 3. Evidence

- **Error log**: [Paste structured log entry or crash artifact]
- **Stack trace**: [Full stack trace]
- **Screenshot / recording**: [If applicable]

## 4. Root Cause Analysis

[5 Whys or description of the root cause once identified]

## 5. Fix

- **Fix description**: [What was changed to resolve the defect]
- **Files changed**: [List of modified files]
- **Regression test**: [Test function name that prevents recurrence — per GOV-002 §21]

## 6. Verification

- [ ] Regression test written and passing
- [ ] Original reproduction steps no longer reproduce the defect
- [ ] No new ERROR/FATAL logs introduced
- [ ] Architect UAT approved
