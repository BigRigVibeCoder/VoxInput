---
id: AGT-NNN-XX
title: "[Agent Role] — Project Boot Document"
type: reference
status: DRAFT
owner: architect
agents: [coder]
tags: [agent-instructions, agentic-development, project-specific]
related: [AGT-002, GOV-007, GOV-008]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** You are the [Frontend/Backend] Developer Agent for [PROJECT_NAME]. This document gives you everything you need to start: your VM, your repo, your tech stack, your binding contracts, and your governance checklist. Read this FIRST, then follow the reading order below.

# [Role Name] — Project Boot Document

---

## 1. Your Environment

| Property | Value |
|:---------|:------|
| **VM / Machine** | `[machine-name]` |
| **Repository** | `[repo-url]` |
| **Service port** | `[port]` |
| **Database** | `[database-name]` on `localhost:5432` |
| **CODEX submodule** | `lexflow-codex/` |

---

## 2. Tech Stack

| Layer | Technology | Version |
|:------|:-----------|:--------|
| Runtime | [Node.js / Python / Go] | [version] |
| Framework | [Next.js / Fastify / Express / Django] | [version] |
| Language | [TypeScript / Python] | strict mode |
| ORM | [Drizzle / Prisma / SQLAlchemy] | [version] |
| Database | [PostgreSQL / MySQL / SQLite] | [version] |
| Testing | [Vitest / Jest / Pytest] | [version] |
| Linting | [ESLint / Ruff] | [version] |

---

## 3. CODEX Reading Order

Read these documents IN THIS ORDER before starting any work:

1. `lexflow-codex/CODEX/00_INDEX/MANIFEST.yaml` — document map
2. `lexflow-codex/CODEX/80_AGENTS/[THIS_FILE]` — your role (this document)
3. `lexflow-codex/CODEX/10_GOVERNANCE/GOV-007_AgenticProjectManagement.md` — PM system
4. `lexflow-codex/CODEX/10_GOVERNANCE/GOV-005_AgenticDevelopmentLifecycle.md` — dev lifecycle
5. `lexflow-codex/CODEX/05_PROJECT/SPR-NNN.md` — your current sprint
6. `lexflow-codex/CODEX/20_BLUEPRINTS/CON-NNN.md` — your binding contracts
7. `lexflow-codex/CODEX/10_GOVERNANCE/GOV-003_CodingStandard.md` — coding rules
8. `lexflow-codex/CODEX/10_GOVERNANCE/GOV-004_ErrorHandlingProtocol.md` — error handling
9. `lexflow-codex/CODEX/10_GOVERNANCE/GOV-006_LoggingSpecification.md` — logging

---

## 4. Binding Contracts

These contracts are **non-negotiable**. Your code MUST match them exactly.

| Contract | What It Governs | Key Sections |
|:---------|:----------------|:-------------|
| `CON-NNN` | [description] | §[sections] |

---

## 5. Database Ownership

You are responsible for creating and maintaining these tables:

| Table | Description |
|:------|:------------|
| `[table_name]` | [description] |

> **No cross-schema foreign keys.** If you need data from another service's database, use the HTTP callback pattern (see CON-001).

---

## 6. Governance Compliance — HARD RULES

> [!CAUTION]
> These are not optional. The Architect WILL reject your branch if any rule is violated.
> The `/git_commit` workflow enforces lint/typecheck/test gates before every commit.

Every task you complete MUST satisfy ALL of the following:

### Testing (GOV-002) — MANDATORY

**Every new source file MUST have a corresponding test file.** This is not negotiable.

| You create... | You MUST also create... |
|:-------------|:-----------------------|
| `src/services/foo.ts` | `src/services/foo.test.ts` |
| `src/routes/bar.ts` | `src/routes/bar.test.ts` |
| `src/plugins/auth.ts` | `src/plugins/auth.test.ts` |

- Test happy path AND error paths (validation, auth, not found, edge cases).
- Run `npm run test` — ALL tests must pass. "Existing tests pass" is NOT sufficient if you added new code without new tests.
- The Architect audits test coverage. Zero tests for new code = automatic rejection.

### Other Governance

- [ ] **GOV-001**: TSDoc/JSDoc on all exported functions. README updated.
- [ ] **GOV-003**: TypeScript strict. No `any`. Complexity ≤10.
- [ ] **GOV-004**: Structured error responses. No unhandled rejections.
- [ ] **GOV-005**: Branch: `feature/SPR-NNN-description` (one per sprint). Commits: `feat(SPR-NNN): T-XXX description`.
- [ ] **GOV-006**: Structured JSON logging. Correlation IDs on requests.
- [ ] **GOV-008**: `.env.example` updated. CODEX submodule linked.

### Commit Workflow

Use `/git_commit` (`.agent/workflows/git_commit.md`) before every commit. It enforces:
1. Branch name validation (GOV-005)
2. Secrets scan — blocks if API keys, PEM blocks, or passwords detected
3. CODEX submodule freshness (GOV-008)
4. `npm run lint && npm run typecheck && npm run test` — all must pass
5. Test coverage — blocks if new source files lack test files

---

## 7. Communication Protocol

| Action | How |
|:-------|:----|
| **Report task complete** | Update task status in sprint doc. Commit and push. |
| **Report blocker** | Create `DEF-NNN.md` in `50_DEFECTS/`. Do NOT work around it. |
| **Propose contract change** | Create `EVO-NNN.md` in `60_EVOLUTION/`. Do NOT self-fix. |
| **Ask a question** | Note it in sprint doc under Blockers. Move to next unblocked task. |

### What You Do NOT Do

- ❌ Modify `CON-` or `BLU-` documents
- ❌ Merge to main without Architect audit
- ❌ Skip tests or governance checks
- ❌ Work around contract ambiguity silently
- ❌ Access another service's database directly
