---
id: BCK-002
title: "Architect Agent Backlog"
type: planning
status: DRAFT
owner: architect
agents: [architect]
tags: [project-management, backlog, architect, audit, deployment]
related: [BCK-001, GOV-007, GOV-008]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** The Architect Agent has its own work stream separate from developer sprints. This backlog tracks: infrastructure prep, sprint audits, contract compliance testing, deployment execution, CODEX maintenance, and agent monitoring. The Architect works **in parallel** with developer agents — never idle.

# Architect Agent Backlog

---

## Work Categories

| Category | Code | Description |
|:---------|:-----|:------------|
| **Infrastructure** | ARCH-INFRA | VM setup, deploy scripts, prod environment |
| **Audit** | ARCH-AUDIT | Sprint audit against contracts + GOV docs |
| **Integration** | ARCH-INTEG | Cross-service contract compliance testing |
| **Deploy** | ARCH-DEPLOY | Production deployment execution |
| **CODEX** | ARCH-CODEX | Document maintenance, MANIFEST, sprint creation |
| **Monitor** | ARCH-MON | Agent progress monitoring, blocker resolution |

---

## Task Template

| ID | Task | Category | Dependencies | Deliverable | Status |
|:---|:-----|:---------|:-------------|:------------|:-------|
| A-NNN | [description] | [category] | [deps] | [what is produced] | [ ] |

---

## Standard Architect Tasks Per Sprint

These tasks repeat for every developer sprint:

1. **A-NNN: Monitor [agent] progress** (ARCH-MON) — check repo for commits, resolve blockers
2. **A-NNN: SPR-NNN Architect Audit** (ARCH-AUDIT) — run VER-001 checklist against completed sprint
3. **A-NNN: Deploy to production** (ARCH-DEPLOY) — after audit passes, deploy and verify health

### First Sprint Additional Tasks

4. **A-001: Verify production VM accessible** (ARCH-INFRA)
5. **A-002: Pre-stage production environment** (ARCH-INFRA)
6. **A-003: Create sprint audit checklist** (ARCH-AUDIT) — VER-001
7. **A-004: Create health check script** (ARCH-INTEG)

### Integration Milestone Tasks (when multiple services connect)

8. **A-NNN: Cross-service contract compliance test** (ARCH-INTEG)
9. **A-NNN: E2E integration test** (ARCH-INTEG)

### Final Sprint Tasks

10. **A-NNN: Archive all sprint docs** (ARCH-CODEX)
11. **A-NNN: Final CODEX reconciliation** (ARCH-CODEX)
12. **A-NNN: Tag release version** (ARCH-DEPLOY)
