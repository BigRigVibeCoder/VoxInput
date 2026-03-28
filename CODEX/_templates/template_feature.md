---
id: EVO-NNN
title: "[Feature name]"
type: reference
status: DRAFT
owner: [agent-name]
agents: [coder, tester]
tags: [feature]
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** [One-sentence summary of the feature and its value.]

# Feature Specification: [Title]

## 1. Overview

| Field | Value |
|:------|:------|
| **Priority** | P0 / P1 / P2 / P3 |
| **Status** | DRAFT / APPROVED / IN-PROGRESS / COMPLETE |
| **Requested By** | Architect / Agent (discovered gap) |
| **Branch** | `feat/EVO-NNN-short-description` |
| **Estimated Scope** | Small (< 1 file) / Medium (2-5 files) / Large (6+ files) |

## 2. Problem Statement

[What problem does this feature solve? Why does it need to exist?]

## 3. Proposed Solution

[How will this be implemented? High-level approach.]

### 3.1 Files to Create or Modify

| Action | File | Purpose |
|:-------|:-----|:--------|
| CREATE | `path/to/new_file.py` | [What it does] |
| MODIFY | `path/to/existing.py` | [What changes] |

### 3.2 Dependencies

[What must exist before this can be built? Other features, libraries, infrastructure.]

## 4. Acceptance Criteria

> **"How do we know this is done?"**

- [ ] [Criterion 1 — specific, verifiable]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## 5. Test Plan

| Test Type | What to Test | Expected Result |
|:----------|:------------|:----------------|
| Unit | [Specific function/behavior] | [Expected outcome] |
| Integration | [Component interaction] | [Expected outcome] |
| E2E | [Full user flow] | [Expected outcome] |

## 6. Checkpoints

| Checkpoint | What Architect Reviews |
|:-----------|:----------------------|
| After spec approval | Does this capture the intent? |
| After core implementation | Does the approach look right? |
| After tests pass | Are we testing the right things? |
| Before merge | Ready for main? |

## 7. Risks & Open Questions

| Risk / Question | Mitigation / Answer |
|:----------------|:-------------------|
| [Risk 1] | [How to handle] |
| [Question 1] | [Pending / Answered] |
