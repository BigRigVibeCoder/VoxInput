---
id: CON-NNN
title: "[Interface or Service Name] Contract"
type: reference
status: DRAFT
owner: architect
agents: [all]
tags: [standards, specification, project-management, governance]
related: [BLU-NNN]
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: 1.0.0
---

> **BLUF:** This contract defines the binding interface rules for [component/service]. All agents building to or consuming this interface MUST conform. No deviation without Human approval.

# [Component/Service Name] — Interface Contract

> **"The contract is truth. The code is an attempt to match it."**

---

## 1. Contract Scope

**What this covers:**
[What interface, API, data exchange, or service boundary does this contract govern?]

**What this does NOT cover:**
[Explicit exclusions to prevent scope creep.]

**Parties:**
| Role | Description |
|:-----|:------------|
| **Producer** | [Who/what generates this interface output] |
| **Consumer** | [Who/what consumes it] |

---

## 2. Version & Stability

| Field | Value |
|:------|:------|
| Contract version | `1.0.0` |
| Stability | `EXPERIMENTAL` / `STABLE` / `DEPRECATED` |
| Breaking change policy | [e.g., "MAJOR version bump required for any breaking change"] |
| Backward compatibility | [e.g., "Consumers must support N-1 versions"] |

---

## 3. Interface Definition

### 3.1 Inputs

| Field | Type | Required | Description | Constraints |
|:------|:-----|:--------:|:------------|:------------|
| `field_name` | `string` | ✅ | [Description] | Max 255 chars |
| `field_name` | `integer` | ❌ | [Description] | Range: 0–100 |

### 3.2 Outputs

| Field | Type | Always present | Description |
|:------|:-----|:--------------:|:------------|
| `field_name` | `string` | ✅ | [Description] |
| `field_name` | `object` | ❌ | [Present when...] |

### 3.3 Example

```json
// Input
{
  "field": "value"
}

// Output (success)
{
  "field": "value"
}
```

### 3.4 TypeScript Schema (if applicable)

> If the project uses TypeScript, provide exact type definitions. Both producer and consumer agents generate their own code from these types — they are the single source of truth.

```typescript
// Request
interface ExampleRequest {
  fieldName: string;
  optionalField?: number;
}

// Response
interface ExampleResponse {
  id: string;
  fieldName: string;
  createdAt: string; // ISO 8601
}

// Error (per GOV-004)
interface ErrorResponse {
  error: {
    code: string;    // e.g., "VALIDATION_ERROR"
    message: string;
    details?: Record<string, string>;
  };
}
```

---

## 4. Error Behavior

All errors conform to `GOV-004_ErrorHandlingProtocol.md`.

| Scenario | Error Category | Response |
|:---------|:--------------|:---------|
| [Missing required field] | `VALIDATION` | [Error response format] |
| [External service unavailable] | `EXTERNAL_SERVICE` | [Fallback behavior] |
| [Unauthorized] | `SECURITY` | [Auth failure response] |

---

## 5. Performance Requirements

| Metric | Requirement |
|:-------|:------------|
| p95 latency | [e.g., < 200ms] |
| p99 latency | [e.g., < 500ms] |
| Throughput | [e.g., > 1000 req/sec] |
| Timeout | [e.g., 30s hard limit] |

---

## 6. Change Protocol

> **This contract is immutable without Human approval.**

To propose a contract change:
1. Developer or Tester opens `60_EVOLUTION/EVO-NNN.md` describing the proposed change
2. Architect reviews and drafts the contract update
3. Human approves the updated contract
4. Version is bumped. All consuming agents are notified.
5. A transition sprint is opened if the change is breaking

---

## 7. Verification Checklist

Tests validating this contract live in `40_VERIFICATION/`. The following must pass before any sprint referencing this contract can close:

- [ ] All required fields validated (§3.1)
- [ ] All error scenarios covered (§4)
- [ ] Performance benchmarks meet §5 thresholds
- [ ] Contract version logged in test report
