---
id: GOV-008
title: "Infrastructure & Operations Standard"
type: reference
status: DRAFT
owner: architect
agents: [all]
tags: [governance, standards, infrastructure, deployment, operations]
related: [GOV-007, BLU-020]
created: 2026-03-24
updated: 2026-03-24
version: 1.0.0
---

> **BLUF:** This document captures all infrastructure decisions that override or adapt the architecture blueprint. It is the bridge between what the blueprint ASSUMES and what the deployment ACTUALLY uses. The Architect MUST complete this document with the Human BEFORE creating the backlog or sprint docs.

# Infrastructure & Operations Standard

> **"Architecture assumes. Infrastructure decides."**

---

## 1. When to Create This Document

This document is created during the **infrastructure governance conversation** — a required discussion between the Human and the Architect Agent before any sprint planning begins. The conversation resolves:

- Deployment model
- Repository structure
- Database ownership
- File storage
- Agent communication protocol
- Shared types strategy

**Rule:** Architecture blueprint (BLU-) + Infrastructure conversation → GOV-008 → THEN create the backlog. Never create the backlog before resolving infrastructure.

---

## 2. Deployment Model

| Decision | Value |
|:---------|:------|
| **Deployment target** | `[Cloud Run / Kubernetes / VM / Serverless / Docker Compose]` |
| **Cloud provider** | `[GCP / AWS / Azure / Self-hosted / None]` |
| **Environment count** | `[dev / staging / prod]` |
| **Production hostname** | `[hostname or TBD]` |

### Adaptation Table

> If the blueprint assumes a different deployment model, document the adaptation here.

| Blueprint Assumption | Actual (GOV-008) |
|:--------------------|:-----------------|
| `[e.g., Cloud Run]` | `[e.g., PM2 on GCP VM]` |
| `[e.g., Cloud SQL]` | `[e.g., Self-managed PostgreSQL]` |
| `[e.g., GCS signed URLs]` | `[e.g., Local disk storage]` |

---

## 3. Repository Structure

| Decision | Value |
|:---------|:------|
| **Structure** | `[Monorepo / Multi-repo with CODEX submodule]` |
| **CODEX repo** | `[repo URL]` |

### Repository Map (Multi-Repo)

| Repository | VM / Machine | Agent | Port | Database |
|:-----------|:-------------|:------|:-----|:---------|
| `[repo-name]` | `[vm-name]` | `[Frontend/Backend]` | `[port]` | `[db-name]` |

### Submodule Configuration

```bash
# Each code repo includes CODEX as a submodule:
git submodule add [CODEX_REPO_URL] lexflow-codex
```

---

## 4. Database Ownership

| Database | Owner Service | Schema Owner Agent | Notes |
|:---------|:-------------|:-------------------|:------|
| `[db_name]` | `[service_name]` | `[Frontend/Backend]` | `[e.g., "No cross-schema FKs"]` |

### Cross-Service Data Access

> How do services that don't own a database access data from it?

`[HTTP callback / Shared read replica / Message queue / N/A]`

---

## 5. File Storage

| Decision | Value |
|:---------|:------|
| **Storage model** | `[Local disk / S3-compatible / Cloud Storage / N/A]` |
| **Storage path** | `[e.g., /var/lexflow/documents/]` |
| **Max file size** | `[e.g., 50MB]` |
| **Allowed types** | `[e.g., pdf, doc, docx, xls, jpg, png]` |

---

## 6. Shared Types Strategy

> How do multiple services share TypeScript (or other language) types?

| Strategy | Description |
|:---------|:------------|
| **(a) npm package** | Publish shared types as an npm package. Both repos install it. |
| **(b) Contract-first** | Types defined only in `CON-` docs. Each agent generates their own. |
| **(c) Copy script** | Script copies type files between repos. |

**Selected:** `[a / b / c]`

**Rationale:** `[Why this choice]`

---

## 7. Service Communication

| Decision | Value |
|:---------|:------|
| **Transport** | `[HTTP / gRPC / Message queue]` |
| **Authentication** | `[Shared secret / mTLS / JWT / None]` |
| **Auth header** | `[e.g., X-Internal-Service-Key]` |
| **Base URLs** | `[e.g., Web: localhost:3000, Trust: localhost:4000]` |

---

## 8. Production Environment

### VM / Server Configuration

| Component | Spec |
|:----------|:-----|
| **OS** | `[e.g., Ubuntu 22.04 LTS]` |
| **Node.js** | `[e.g., 20 LTS]` |
| **Process manager** | `[e.g., PM2 / systemd]` |
| **Reverse proxy** | `[e.g., nginx]` |
| **TLS** | `[e.g., Let's Encrypt / Cloudflare / None]` |
| **Firewall** | `[e.g., UFW: 22, 80, 443]` |

### Directory Layout

```
/opt/[project]/
├── frontend/    # Web service code
├── backend/     # API service code
└── scripts/     # Deployment and provisioning scripts
```

---

## 9. Backup & Recovery

| Decision | Value |
|:---------|:------|
| **Backup method** | `[pg_dump cron / managed snapshots / N/A]` |
| **Frequency** | `[daily / hourly]` |
| **Retention** | `[e.g., 7 days rolling]` |
| **Restore procedure** | `[scripts/restore.sh or documented steps]` |

---

## 10. Monitoring & Observability

| Decision | Value |
|:---------|:------|
| **Error tracking** | `[Sentry / Datadog / None]` |
| **Log aggregation** | `[Structured JSON to files / CloudWatch / None]` |
| **Health checks** | `[e.g., GET /health on each service]` |
| **Uptime monitoring** | `[UptimeRobot / custom / None]` |
