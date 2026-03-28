---
id: BLU-020
title: "CODEX System Blueprint — How the Agentic Architect Governs AI Agents"
type: explanation
status: DRAFT
owner: architect
agents: [all]
tags: [governance, documentation, codex, standards, architecture, workflow]
related: [GOV-001, GOV-002, GOV-003, GOV-004, GOV-005, GOV-006, RUN-DG-001]
created: 2026-03-17
updated: 2026-03-17
version: 1.0.0
---

> **BLUF:** The CODEX is a machine-readable, NASA/JPL-grade documentation engine that governs AI agents through structured protocols, mandatory compliance checks, and a dual-audience architecture. This blueprint explains exactly how the system works, what workflows enforce compliance, what documents are missing, and how control can be improved.

# CODEX System Blueprint

> **"If an agent can't parse it, it doesn't exist. If a human can't skim it, it's useless."**

---

## 1. What Is the CODEX?

The CODEX (**CO**ntrolled **D**ocumentation **EX**change) is the centralized knowledge engine for any project built with the Agentic Architect template. It is a **hybrid documentation system** that combines:

| Influence | What It Provides |
|:----------|:----------------|
| **Johnny.Decimal** | Deterministic numeric sorting (00–90) so `ls` always shows files in order |
| **PARA** | Lifecycle stages: active → archived (status field in frontmatter) |
| **Diátaxis** | Content types: `reference`, `how-to`, `tutorial`, `explanation` |
| **NASA-HDBK-2203** | Formal verification, traceability, change control |
| **DO-178C** | Requirements traceability, peer review gates |

### 1.1 Design Principle: Dual-Audience

Every file is designed for two consumers simultaneously:

- **Humans** — Skim BLUFs, browse README indexes, review at checkpoints
- **AI Agents** — Parse YAML frontmatter, filter MANIFEST.yaml, execute from tags/type/status

This is what makes the CODEX fundamentally different from traditional docs-as-code: the documentation is both **human-readable** and **machine-executable**.

---

## 2. CODEX Area Architecture

```
CODEX/
├── 00_INDEX/          ← Discovery layer (MANIFEST.yaml, TAG_TAXONOMY.yaml)
├── 10_GOVERNANCE/     ← The Laws (GOV-001 through GOV-006)
├── 20_BLUEPRINTS/     ← The Designs (BLU-NNN specs)
├── 30_RUNBOOKS/       ← The Procedures (RUN-NNN how-tos)
├── 40_VERIFICATION/   ← The Proof (VER-NNN test reports)
├── 50_DEFECTS/        ← The Forensics (DEF-NNN bug reports)
├── 60_EVOLUTION/      ← The Roadmap (EVO-NNN feature specs)
├── 70_RESEARCH/       ← The Science (RES-NNN investigations)
├── 90_ARCHIVE/        ← The History (deprecated docs)
└── _templates/        ← Scaffolding (Diátaxis templates)
```

### 2.1 Area Rules

1. **Numerical prefixes** (`00_`, `10_`, ..., `90_`) force deterministic sort order
2. **Category codes** map to areas: GOV → 10, BLU → 20, RUN → 30, VER → 40, DEF → 50, EVO → 60, RES → 70
3. **One area, one purpose** — no overlapping scope
4. **Every area has a README.md** explaining what belongs there

---

## 3. The Three Discovery Mechanisms

Agents find documents through three complementary channels:

### 3.1 MANIFEST.yaml (The Agent's Map)

Located at `CODEX/00_INDEX/MANIFEST.yaml`. A single YAML file that indexes every document with:
- `id`, `path`, `title`, `type`, `status`, `tags`, `agents`, `summary`

An agent parses this one file to locate exactly the docs it needs — **no directory crawling required**.

### 3.2 TAG_TAXONOMY.yaml (Controlled Vocabulary)

Located at `CODEX/00_INDEX/TAG_TAXONOMY.yaml`. A curated taxonomy of allowed tags organized into groups (governance, engineering, infrastructure, etc.). Agents and humans cannot invent ad-hoc tags — all tags must exist in this taxonomy.

### 3.3 README.md (The Human Map)

Located at `CODEX/00_INDEX/README.md`. A human-readable overview with links to all areas and key documents.

---

## 4. Document Anatomy

Every CODEX document follows a strict structure:

### 4.1 YAML Frontmatter (11 Required Fields)

```yaml
---
id: GOV-001              # Category code + sequence number
title: "Document Title"   # Human-readable name
type: reference           # reference | how-to | tutorial | explanation
status: APPROVED          # DRAFT | REVIEW | APPROVED | DEPRECATED
owner: architect          # Who is responsible
agents: [all]             # Which agents should read this
tags: [governance, ...]   # Controlled tags from TAG_TAXONOMY.yaml
related: [GOV-002, ...]   # Cross-references to other CODEX docs
created: 2026-03-04       # Creation date
updated: 2026-03-04       # Last modified date
version: 1.0.0            # Semantic version
---
```

### 4.2 BLUF-First Content

The first line after frontmatter must be a **Bottom Line Up Front**:
```markdown
> **BLUF:** [One-sentence summary that tells you everything you need to know]
```

### 4.3 Size Constraint

| Size | Status |
|:-----|:-------|
| ≤10KB | ✅ Ideal |
| 10–30KB | ⚠️ Warning — consider splitting |
| 30KB+ | 🔴 Violation — must justify or split |

---

## 5. The Governance Stack (10_GOVERNANCE)

Six governance documents form the legal framework for all agent behavior:

| ID | Document | What It Controls |
|:---|:---------|:----------------|
| **GOV-001** | Documentation Standard | How docs are written, named, versioned, archived |
| **GOV-002** | Testing Protocol | 14-tier NASA/JPL test pyramid, assertion density, forensic artifacts |
| **GOV-003** | Coding Standard | Python/C/React coding rules, incident-readability, static analysis |
| **GOV-004** | Error Handling Protocol | Zero-dark-failure, crash artifacts, circuit breakers, correlation IDs |
| **GOV-005** | Agentic Development Lifecycle | Sprint model, branch strategy, checkpoints, merge/deploy gates |
| **GOV-006** | Logging Specification | Structured logging, trace-first design, forensic query patterns |

### 5.1 How Governance Controls Agents

1. **Agent reads `.agent/context.md`** on project entry — told to read `10_GOVERNANCE/` first
2. **Frontmatter `agents` field** specifies which agents must comply (`[all]` for governance)
3. **Cross-references** (`related`) create a compliance web — every GOV doc points to others
4. **Verification checklist** (GOV-005 §6.1) gates every merge on compliance
5. **`/manage_documents` workflow** enforces frontmatter validity and tag compliance

---

## 6. Compliance Workflows

### 6.1 `/manage_documents` — CODEX Maintenance

The primary compliance enforcement workflow. Runs 4 phases:

| Phase | What It Does |
|:------|:------------|
| **Phase 1: Scan** | Finds all markdown files, extracts frontmatter |
| **Phase 2: Doc-Lint** | Validates frontmatter fields, tag taxonomy, BLUF presence, size limits, cross-references |
| **Phase 3: Regenerate** | Rebuilds MANIFEST.yaml from scanned frontmatter |
| **Phase 4: Report** | Prints compliance report with all violations |

**Key enforcement rules:**
- All 11 frontmatter fields must be present
- All tags must exist in TAG_TAXONOMY.yaml
- All cross-referenced IDs must resolve to real documents
- Documents must contain a BLUF line
- No placeholder text (TODO, TBD, FIXME)

### 6.2 `/git_commit` — Forensic Commit Hygiene

Ensures every commit includes:
- Secret scanning on staged diffs
- Structured commit messages with `Why`, `What`, `Agent`, `Refs` fields
- CODEX document ID traceability

### 6.3 `/test` — NASA-Grade Verification

Auto-detects the project stack and runs GOV-002 tiers:
- Static analysis, unit tests, integration tests
- Coverage thresholds, assertion density
- Forensic artifact generation

---

## 7. The Agentic Loop

Every piece of work follows a 6-phase lifecycle (GOV-005):

```
CONVERSATION → SPECIFICATION → SPRINT → VERIFICATION → MERGE → DEPLOY
      ↑                                                            |
      └──────────── Gaps, bugs, ideas re-enter ────────────────────┘
```

**Key control points:**
- Specs must exist before code is written
- One agent per branch, one branch per purpose
- Checkpoints at 5 natural stopping points
- No merge without passing tests AND Architect approval
- Architect triggers all deployments

---

## 8. Current State Assessment

### 8.1 What Exists (✅)

| Component | Status |
|:----------|:-------|
| CODEX directory structure (10 areas) | ✅ Complete |
| 6 governance documents (GOV-001–006) | ✅ Approved |
| MANIFEST.yaml with full schema | ✅ Active |
| TAG_TAXONOMY.yaml | ✅ Curated |
| Agent context (`.agent/context.md`) | ✅ Complete |
| 8 agent workflows (git, docs, test, DG) | ✅ Active |
| 1 runbook (DarkGravity setup/recovery) | ✅ Approved |

### 8.2 What Is Missing (❌)

| Gap | Impact | Recommended Action |
|:----|:-------|:------------------|
| **No Agent Permission/Scope Standard** | Agents have no formal boundaries on what they can modify | Create GOV-007 |
| **No Security Standard** | No secrets management, access control, or supply chain rules | Create GOV-008 |
| **No Data Governance** | No rules on data handling, PII, retention, or classification | Create GOV-009 |
| **No Change Management Protocol** | No formal approval gates, rollback procedures, or audit trail requirements beyond commits | Create GOV-010 |
| **No Compliance Workflow** | `/manage_documents` checks doc quality but not agent behavioral compliance | Create `/compliance_check` workflow |
| **Empty BLUEPRINTS area** | No project-specific specs exist yet | Expected for template |
| **Empty VERIFICATION area** | No test specs or QA reports | Expected for template |
| **No Agent Capability Registry** | No formal catalog of what each agent can/cannot do | Add to GOV-007 or create BLU doc |
| **No Incident Response Runbook** | No procedure for when an agent produces harmful or incorrect output | Create RUN-002 |
| **No Prompt Governance** | No standard for system prompts, context injection, or prompt versioning | Create GOV-011 or RES doc |

---

## 9. DarkGravity Swarm Integration

The template includes 5 DarkGravity workflows that connect the CODEX to the multi-agent swarm:

| Workflow | Stages | How It Uses CODEX |
|:---------|:-------|:-----------------|
| `/darkgravity_research` | Researcher | Outputs feed `70_RESEARCH/` |
| `/darkgravity_architect` | Architect | Generates task backlogs for `60_EVOLUTION/` |
| `/darkgravity_coder` | Coder + Tester | Implements specs from `20_BLUEPRINTS/` |
| `/darkgravity_swarm` | All 4 stages | Full pipeline across CODEX areas |
| `/darkgravity_setup` | N/A | Bootstrap documented in `30_RUNBOOKS/RUN-DG-001` |

---

## 10. Improvement Recommendations

### 10.1 Near-Term (Add to Governance)

1. **GOV-007: Agent Permissions & Scope** — Define read/write/execute boundaries per agent role
2. **GOV-008: Security Standard** — Secrets, supply chain, access control
3. **GOV-009: Data Governance** — PII handling, data classification, retention
4. **GOV-010: Change Management** — Approval gates, rollback procedures, audit requirements

### 10.2 Near-Term (Add Workflows)

1. **`/compliance_check`** — Automated compliance audit against all GOV docs
2. **`/incident_response`** — Procedures for agent-produced errors or harmful output
3. **`/onboard_agent`** — Standardized agent initialization and capability registration

### 10.3 Medium-Term (Research Needed)

1. **Prompt governance and versioning** — How to track system prompt changes
2. **Multi-agent conflict resolution** — What happens when agents disagree
3. **Agent observability and telemetry** — Runtime monitoring of agent behavior
4. **Guardrails and safety boundaries** — Output validation, content filtering
5. **Cost governance** — Token budgets, model selection policies

---

> **"The CODEX is the constitution. The governance docs are the laws. The workflows are the enforcement. The Architect is the judge."**
