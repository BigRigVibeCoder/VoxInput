---
id: GOV-005
title: "Agentic Development Lifecycle"
type: reference
status: APPROVED
owner: architect
agents: [all]
tags: [governance, standards, project-management, workflow]
related: [GOV-001, GOV-002, GOV-003, GOV-004, GOV-006]
created: 2026-03-04
updated: 2026-03-04
version: 2.0.0
---

> **BLUF:** Project lifecycle protocol for human-Architect + AI-agent development. Replaces traditional Agile with scope-bounded sprints, emergent work items, one-agent-per-branch execution, natural checkpoints, and human-in-the-loop merge/deploy. The only human in the loop is the Architect. Everything else is agentic.

# Agentic Development Lifecycle

> **"The Architect thinks. The agents build. The tests prove. The logs remember."**

---

## 1. Philosophy: Why This Isn't Agile

Traditional Agile assumes a team of humans who need ceremonies (standups, retros, planning poker) to synchronize. Agentic Development has **one human Architect + N AI agents** that execute in minutes. The ceremonies are replaced by **conversations**.

| Agile | Agentic Development |
|:------|:-------------------|
| Sprint = 2 weeks | Sprint = **scope-bounded** (one feature, one bug, one research) |
| Sprint planning meeting | **Conversation** → formal spec in minutes |
| Daily standup | Doesn't exist — agents work, Architect reviews |
| Sprint review / retro | **Checkpoint** — natural stopping point to assess |
| Product backlog groomed by humans | **Emergent** — gaps, test failures, and ideas create work items in real-time |
| Team of 5-9 humans | **1 Architect + N agents**, one per branch |
| PRs reviewed by teammates | **Agentic merge** with Architect in the loop |
| CI/CD runs automatically | **Agentic CI/CD** with Architect in the loop |

### 1.1 The Three Roles

| Role | Who | Responsibility |
|:-----|:----|:---------------|
| **Architect** | Human (you) | Vision, decisions, approval, sanity checks |
| **Agent** | AI | Research, coding, testing, documentation, deployment |
| **Protocol** | This document + GOV-001–006 | Rules that agents follow without asking |

---

## 2. The Agentic Loop

Every piece of work — feature, bug, research — follows this loop:

```
    ┌──────────────────────────────────────────────────┐
    │               THE AGENTIC LOOP                    │
    │                                                  │
    │  1. CONVERSATION ←→ Architect + Agent discuss    │
    │         ↓                                        │
    │  2. SPECIFICATION → Agent writes formal spec     │
    │         ↓                                        │
    │  3. SPRINT → Agent executes on a branch          │
    │         ↓ (checkpoints as needed)                │
    │  4. VERIFICATION → Tests + Architect review      │
    │         ↓                                        │
    │  5. MERGE → Agentic merge + Architect approval   │
    │         ↓                                        │
    │  6. DEPLOY → Agentic deploy + Architect trigger  │
    │         ↓                                        │
    │  ↻ Gaps, bugs, ideas re-enter at step 1          │
    └──────────────────────────────────────────────────┘
```

---

## 3. Phase 1: Conversation

The Architect and an agent discuss what needs to be built. This replaces sprint planning, user story writing, and backlog grooming — all in one conversation.

### 3.1 What Happens

1. Architect describes the need (feature, bug fix, research question)
2. Agent asks clarifying questions
3. They iterate until the scope is clear
4. Agent produces a **formal specification** (Phase 2)

### 3.2 Rules

- **Every conversation that results in work MUST produce a spec.** No building from memory.
- The agent should challenge vague requirements — "What does 'fast' mean? What's the latency budget?"
- The Architect has final say on scope decisions.

---

## 4. Phase 2: Specification

The agent writes a formal document based on the conversation. The document type depends on the work item:

| Work Type | Template | CODEX Location | ID Prefix |
|:----------|:---------|:---------------|:----------|
| **New Feature** | `template_feature.md` | `60_EVOLUTION/` | `EVO-NNN` |
| **Bug Fix** | `template_defect.md` | `50_DEFECTS/` | `DEF-NNN` |
| **Research / Investigation** | `template_research.md` | `70_RESEARCH/` | `RES-NNN` |
| **System Design** | `template_reference.md` | `20_BLUEPRINTS/` | `BLU-NNN` |

### 4.1 Rules

- The spec is written **before any code is written**.
- The Architect reviews the spec and says "go" or "change X."
- The spec becomes the source of truth — tests trace back to it (GOV-002 §19).
- Specs are versioned and live in CODEX permanently.

---

## 5. Phase 3: Sprint

A sprint is **scope-bounded, not time-bounded.** It runs until the spec is implemented, tested, and verified — whether that takes 5 minutes or 5 hours.

### 5.1 Branch Strategy

**One agent, one branch per sprint. Granular commits, not granular branches.**

> [!IMPORTANT]
> Do NOT create a separate branch per task within a sprint. Tasks within a sprint
> are tightly coupled — separate branches add merge complexity without review value.

#### Branch Naming

| Scenario | Naming Convention | Example |
|:---------|:-----------------|:--------|
| **Single-agent sprint** | `feature/SPR-NNN-short-description` | `feature/SPR-004-trust-accounting` |
| **Multi-agent sprint** (per agent) | `feature/SPR-NNN-agent-short-desc` | `feature/SPR-005-frontend-trust-ui` |
| Bug Fix | `fix/DEF-NNN-short-description` | `fix/DEF-003-missing-tests` |
| Hotfix | `hotfix/DEF-NNN-short-description` | `hotfix/DEF-010-auth-bypass` |
| Deploy | `deploy/vX.Y.Z` | `deploy/v0.2.0` |

#### Commit Granularity (within the branch)

Each task gets its own commit. This gives you task-level traceability via `git log`:

```
feat(SPR-004): T-034 trust schema + migration
feat(SPR-004): T-038 ledger engine with advisory locks
feat(SPR-004): T-040 deposit route
feat(SPR-004): T-041 disburse route
test(SPR-004): unit tests for all routes and ledger engine
```

### 5.2 Branch Rules

1. **Branch from `main`** — always start from the latest stable.
2. **One agent per branch** — no two agents working on the same branch.
3. **One branch per sprint per agent** — do NOT create per-task branches.
4. **Branch names include the sprint ID** — traceability from branch to spec.
5. **Short-lived branches** — merge or close within the sprint. No stale branches.
6. **Delete after merge** — the Architect deletes feature branches after auditing and merging. No branch accumulation.
5. **Commit messages** follow this format (optimized for agent readability):

```
type(scope): short description

Why: [reason this change exists]
What: [what was changed]
Agent: [which agent made the change]
Refs: [CODEX document IDs]
```

### 5.3 Checkpoints

Checkpoints are **natural stopping points** where the Architect can assess progress. They are not formal gates — they're sanity checks.

**When checkpoints occur:**

| Checkpoint | What Happens |
|:-----------|:-------------|
| **After spec generation** | Architect reviews: "Does this capture what I want?" |
| **After core implementation** | Architect reviews: "Does this look right? Any concerns?" |
| **After test suite runs** | Architect reviews: "Are we testing the right things? All passing?" |
| **Before merge** | Architect reviews: "Is this ready for main?" |
| **After deploy** | Architect verifies: "Is this working in production?" |

**What happens at a checkpoint:**
- Agent presents current state (what's done, what's next, any concerns)
- Architect may ask questions, request changes, or approve
- Testing can be triggered at any checkpoint
- The sprint continues or pivots based on the conversation

**Checkpoints are not blockers** — they're the Architect's opportunity to steer. If the Architect says "looks good, keep going," the agent continues without delay.

---

## 6. Phase 4: Verification

Testing is agentic but human-in-the-loop. The agent runs the test suite per GOV-002, and the Architect reviews the results.

### 6.1 Verification Checklist

The agent runs through this checklist during verification:

- [ ] Static analysis passes (GOV-002 §3, GOV-003 §12)
- [ ] Unit tests pass with ≥80% coverage (GOV-002 §4)
- [ ] All applicable test tiers pass (GOV-002 §2)
- [ ] No forbidden patterns detected (GOV-003 §5.5, GOV-004 §9)
- [ ] Error handling compliant (GOV-004)
- [ ] Logging instrumented (GOV-006 §8)
- [ ] Crash artifacts configured (GOV-004 §6)
- [ ] Test artifacts generated (GOV-002 §17)

### 6.2 The Architect's UAT

After automated verification, the Architect performs User Acceptance Testing:

1. Agent demonstrates the feature / fix / research outcome
2. Architect verifies it matches the original spec
3. Architect may test edge cases conversationally ("What happens if...?")
4. Architect approves or requests changes

---

## 7. Phase 5: Merge

Merging is agentic with Architect approval.

### 7.1 Merge Process

1. Agent opens a merge (PR or direct merge depending on the project)
2. Agent provides a merge summary:
   - What changed (file list, line counts)
   - Which spec it implements (CODEX ID)
   - Test results summary
   - Any risks or known limitations
3. Architect reviews and approves
4. Agent performs the merge
5. Agent deletes the feature branch

### 7.2 Merge Rules

- **No merge without passing tests** — automated verification must pass first.
- **No merge without Architect approval** — this is not optional.
- **Squash or rebase** — keep history clean. No merge commits unless necessary.
- **Update MANIFEST.yaml** — if new docs were created, update the registry.

---

## 8. Phase 6: Deploy

Deployment is agentic with Architect trigger.

### 8.1 Deployment Process

1. Agent prepares deployment on a `deploy/vX.Y.Z` branch
2. Agent runs full verification suite against the deploy branch
3. Agent presents deployment plan to Architect
4. **Architect triggers deploy** — this is always a human decision
5. Agent executes deployment steps
6. Agent verifies deployment (health checks, smoke tests)
7. Architect confirms success

### 8.2 Version Numbering

Follow Semantic Versioning:

| Change | Version | Example |
|:-------|:--------|:--------|
| Breaking change | **X**.0.0 | 1.0.0 → 2.0.0 |
| New feature | x.**Y**.0 | 1.0.0 → 1.1.0 |
| Bug fix | x.y.**Z** | 1.0.0 → 1.0.1 |

---

## 9. Work Item Lifecycle

Work items emerge organically — from conversations, testing gaps, bugs discovered during implementation, or Architect ideas.

### 9.1 How Work Items Are Created

| Source | What Happens |
|:-------|:-------------|
| **Architect has an idea** | Conversation → Spec → Sprint |
| **Agent discovers a gap** | Agent flags it → Architect decides priority → Spec if approved |
| **Test fails** | Defect report created → Sprint to fix |
| **E2E/integration reveals issue** | Defect report → Root cause analysis → Fix sprint |
| **Research needed before building** | Research spec → Investigation sprint → Findings doc |

### 9.2 Work Item Priorities

| Priority | Definition | Response |
|:---------|:-----------|:---------|
| **P0 — Critical** | Production broken, data loss, security breach | Sprint immediately. Everything else stops. |
| **P1 — High** | Major feature blocked, significant bug | Sprint next. |
| **P2 — Medium** | Important but not blocking | Sprint when current work completes. |
| **P3 — Low** | Nice to have, cosmetic, optimization | Sprint when nothing higher is pending. |

---

## 10. Project Bootstrapping

When starting a new project with the Agentic Architect template:

### 10.1 Day Zero Checklist

1. **Pull in the template** — `agentic_architect` provides CODEX structure + all GOV docs
2. **Conversation** — Architect describes the project to an agent
3. **Agent writes the initial spec** — `BLU-001_ProjectSpecification.md` in `20_BLUEPRINTS/`
4. **Agent sets up the project** — scaffolding, dependencies, CI/CD
5. **Agent configures governance** — static analysis (GOV-003 §12), logging (GOV-006), error handling (GOV-004)
6. **First checkpoint** — Architect reviews scaffolding before any features are built
7. **Sprint 1 begins** — first feature from the spec

### 10.2 What the Agent Does Automatically

When "set up a new project" is requested:

- [ ] Create initial `BLU-001_ProjectSpecification.md` from conversation
- [ ] Configure static analysis profiles per GOV-003 §12
- [ ] Set up logging per GOV-006 §5-7
- [ ] Install global exception handlers per GOV-004 §4
- [ ] Create test infrastructure per GOV-002 §25
- [ ] Initialize git with proper `.gitignore` and branch structure
- [ ] Create `.env.example` per GOV-006 §11
- [ ] Update MANIFEST.yaml with initial documents

---

## 11. Compliance Checklist

Before deploying any project milestone:

- [ ] All work items traced to CODEX specs (GOV-001 §10)
- [ ] All branches follow naming convention (§5.1)
- [ ] All commits follow message format (§5.2)
- [ ] All sprints started from a formal spec (§4)
- [ ] All checkpoints documented in conversation history
- [ ] Automated verification passed (§6.1)
- [ ] Architect UAT completed (§6.2)
- [ ] Merge approved by Architect (§7)
- [ ] MANIFEST.yaml up to date
- [ ] No stale branches remaining

---

## 12. Agent Instructions

When an Architect starts a new conversation about building something:

1. **Ask clarifying questions** — don't assume. Challenge vague requirements.
2. **Write a formal spec** — feature (EVO-*), defect (DEF-*), or research (RES-*) per §4.
3. **Get Architect approval** on the spec before writing code.
4. **Create a branch** with proper naming per §5.1.
5. **Implement with checkpoints** — pause at natural stopping points per §5.3.
6. **Run verification** — full test suite per §6.1.
7. **Present results** to Architect for UAT per §6.2.
8. **Merge** with Architect approval per §7.
9. **Document** — update MANIFEST, close work items, delete branch.

---

> **"Fast doesn't mean reckless. It means every minute counts, every spec is clear, and every test proves the work."**
