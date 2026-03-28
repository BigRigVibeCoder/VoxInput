# 05_PROJECT — Active Project State

This area contains the live project management state. It is the operational layer of the CODEX markdown operating system.

## What Lives Here

| Prefix | What It Is | Agile Equivalent |
|:-------|:-----------|:-----------------|
| `PRJ-` | Project roadmap and vision | Initiative / Epic |
| `SPR-` | Individual sprint documents | Sprint |
| `BCK-` | Prioritized backlog | Product Backlog |

## Rules

- **PRJ- docs** are owned by the Human. Architect Agent may propose changes.
- **SPR- docs** are created by the Architect Agent and assigned to Developer/Tester Agents.
- **Closed sprints** move to `90_ARCHIVE/` when status reaches `CLOSED`.
- **This directory should always reflect the current sprint state.** Active sprints only.

## See Also

- `10_GOVERNANCE/GOV-007_AgenticProjectManagement.md` — full PM system definition
- `80_AGENTS/` — agent role definitions
- `20_BLUEPRINTS/` — contracts and design specs agents execute against
