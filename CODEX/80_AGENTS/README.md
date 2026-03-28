# 80_AGENTS — Agent Role Definitions

This area contains the agent role definition templates used to spin up new Architect, Developer, and Tester agents on any project.

## What Lives Here

| File | Role | Spin up when... |
|:-----|:-----|:----------------|
| `AGT-001_Architect_Agent.md` | Architect Agent | Starting a new project or new Architect session |
| `AGT-002_Developer_Agent.md` | Developer Agent | Assigning a developer to a sprint |
| `AGT-003_Tester_Agent.md` | Tester Agent | Beginning a verification sprint |

## How to Use

1. Copy the relevant `AGT-` file contents into a new agent session's system context
2. Fill in the `[PROJECT_NAME]`, `[REPO_PATH]`, and `[SPRINT_ID]` placeholders
3. Point the agent at the relevant CODEX documents for its first read

## Rules

- Agent definitions are **role templates**, not project-specific profiles
- They explain the PM system, the CODEX structure, and the agent's scope
- They are intentionally **coding-language agnostic** — the agent learns the tech stack from the blueprints and contracts
- New role types may be added here as the project scales (e.g., `AGT-004_DevOps_Agent.md`)

## See Also

- `10_GOVERNANCE/GOV-007_AgenticProjectManagement.md` — full PM system definition
- `05_PROJECT/` — active sprint and roadmap docs agents will be assigned
