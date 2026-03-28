---
id: IDX-000
title: "Documentation Master Index"
type: reference
status: APPROVED
owner: architect
agents: [all]
created: 2026-03-04
updated: 2026-03-18
version: 2.0.0
---

> **BLUF:** This is the single entry point for all project documentation. Humans start here. Agents read `MANIFEST.yaml`.

# 📚 Documentation Master Index

> **"If it isn't documented, it doesn't exist."**

Welcome to the project knowledge base. This documentation system is designed for **dual-audience** consumption: human agentic architects and AI coding agents.

---

## System Overview

| Component | Purpose |
|:----------|:--------|
| `MANIFEST.yaml` | Machine-readable registry of ALL docs — the agent's map |
| `_templates/` | Doc templates for each Diátaxis type |
| `GOV-001` | The meta-standard governing this entire system |

### How to Use This System

**Humans**: Browse the index below. Each area is numbered for deterministic sort order.

**Agents**: Parse `00_INDEX/MANIFEST.yaml`. Filter by `tags`, `status`, `type`, or `agents` field to find relevant docs without directory crawling.

---

## 05. PROJECT — *The Active State*

> Active project management state. Roadmap, sprints, backlog. The operational layer of the CODEX OS.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — add PRJ-, SPR-, BCK- docs when your project starts)* | | | |

**Category Codes**: `PRJ` (Project Roadmap), `SPR` (Sprint), `BCK` (Backlog)

---

## 10. GOVERNANCE — *The Laws*

> Standards, protocols, coding rules, architecture decisions. These docs **govern** how agents and humans operate.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| [GOV-001](../10_GOVERNANCE/GOV-001_DocumentationStandard.md) | Documentation Standard | reference | APPROVED |
| [GOV-002](../10_GOVERNANCE/GOV-002_TestingProtocol.md) | Testing Protocol | reference | APPROVED |
| [GOV-003](../10_GOVERNANCE/GOV-003_CodingStandard.md) | Coding Standard | reference | APPROVED |
| [GOV-004](../10_GOVERNANCE/GOV-004_ErrorHandlingProtocol.md) | Error Handling Protocol | reference | APPROVED |
| [GOV-005](../10_GOVERNANCE/GOV-005_AgenticDevelopmentLifecycle.md) | Agentic Development Lifecycle | reference | APPROVED |
| [GOV-006](../10_GOVERNANCE/GOV-006_LoggingSpecification.md) | Logging Specification | reference | APPROVED |
| [GOV-007](../10_GOVERNANCE/GOV-007_AgenticProjectManagement.md) | Agentic Project Management Standard | reference | APPROVED |

**Category Codes**: `GOV` (Governance), `ADR` (Architecture Decision Record)

---

## 20. BLUEPRINTS — *The Designs*

> Component specifications, system designs, API contracts. What agents build FROM.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| [BLU-020](../20_BLUEPRINTS/BLU-020_CODEX_System_Blueprint.md) | CODEX System Blueprint | explanation | DRAFT |
| *(add BLU- design specs and CON- contracts as project grows)* | | | |

**Category Codes**: `BLU` (Blueprint/Spec), `CON` (Contract/Interface)

---

## 30. RUNBOOKS — *The Procedures*

> Operational how-to guides, deployment procedures, workflows. Step-by-step executable instructions.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| [RUN-DG-001](../30_RUNBOOKS/RUN-DG-001_DarkGravity_Setup_Recovery.md) | DarkGravity Setup & Recovery Guide | how-to | APPROVED |

**Category Codes**: `RUN` (Runbook/Guide), `DEP` (Deployment)

---

## 40. VERIFICATION — *The Proof*

> Test specifications, QA standards, validation reports, acceptance criteria.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — add verification docs as the project grows)* | | | |

**Category Codes**: `VER` (Verification), `QA` (Quality Assurance)

---

## 50. DEFECTS — *The Forensics*

> Bug reports, root cause analysis, incident forensics, post-mortems.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — add defect reports as the project grows)* | | | |

**Category Codes**: `DEF` (Defect), `RCA` (Root Cause Analysis)

---

## 60. EVOLUTION — *The Roadmap*

> Feature specifications, enhancement proposals, roadmaps. Planned changes that evolve the system.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — add evolution docs as the project grows)* | | | |

**Category Codes**: `EVO` (Evolution/Feature), `RFC` (Request for Change)

---

## 70. RESEARCH — *The Science*

> Whitepapers, investigations, proof-of-concepts, literature reviews.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — add research papers as the project grows)* | | | |

**Category Codes**: `RES` (Research), `POC` (Proof of Concept)

---

## 90. ARCHIVE — *The History*

> Deprecated, completed, and historical docs. Preserved for reference, not for active use.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| *(empty — docs move here when deprecated)* | | | |

---

## 80. AGENTS — *The Team*

> Agent role definitions. Spin up Architect, Developer, or Tester agents from these templates.

| ID | Title | Type | Status |
|:---|:------|:-----|:-------|
| [AGT-001](../80_AGENTS/AGT-001_Architect_Agent.md) | Architect Agent — Role Definition | reference | APPROVED |
| [AGT-002](../80_AGENTS/AGT-002_Developer_Agent.md) | Developer Agent — Role Definition | reference | APPROVED |
| [AGT-003](../80_AGENTS/AGT-003_Tester_Agent.md) | Tester Agent — Role Definition | reference | APPROVED |

**Category Codes**: `AGT` (Agent Definition)

---

## Templates

| Template | Diátaxis Type | Use When |
|:---------|:-------------|:---------|
| [template_reference.md](../_templates/template_reference.md) | Reference | Documenting facts: specs, APIs, schemas, configs |
| [template_how-to.md](../_templates/template_how-to.md) | How-To | Writing step-by-step procedures to solve a specific problem |
| [template_tutorial.md](../_templates/template_tutorial.md) | Tutorial | Teaching through a guided learning experience |
| [template_explanation.md](../_templates/template_explanation.md) | Explanation | Explaining concepts, architecture, design decisions |
| [template_sprint.md](../_templates/template_sprint.md) | SPR- Sprint | Creating a new sprint document |
| [template_contract.md](../_templates/template_contract.md) | CON- Contract | Defining an interface contract |
| [template_project_roadmap.md](../_templates/template_project_roadmap.md) | PRJ- Roadmap | Writing the project vision and delivery phases |

---

## Document Lifecycle

```
DRAFT → REVIEW → APPROVED → DEPRECATED → ARCHIVE
```

| Status | Meaning |
|:-------|:--------|
| **DRAFT** | Work in progress, not reviewed |
| **REVIEW** | Ready for peer/agent review |
| **APPROVED** | Frozen, ready for use |
| **DEPRECATED** | Superseded — will move to `90_ARCHIVE/` |

---

> **"Documentation is not about recording what you did. It's about enabling what comes next."**
