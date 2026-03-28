---
description: Comprehensive governance compliance scan — checks all 8 GOV docs against staged/changed source files. Called by /git_commit automatically, or run standalone for architect audits.
---

# /governance_scan — Comprehensive Governance Compliance Check

## Overview

This workflow scans source files against all 8 governance documents (GOV-001 through GOV-008).
It is designed to be called by `/git_commit` as a pre-commit gate, or run standalone by the Architect for sprint audits.

**Who runs this:**
- **Developer agents** — automatically via `/git_commit` before every commit
- **Architect agent** — standalone during sprint audits (`/governance_scan`)

**Behavior:**
- Each check produces a PASS/FAIL/WARN result
- Any FAIL blocks the commit (when called from `/git_commit`)
- WARNings are reported but do not block
- Results are printed as a summary table at the end

---

## Step 1: Identify Target Files

Determine which files to scan:

```bash
# If called from /git_commit, scan staged files only:
SCAN_FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|tsx)$' | grep -v node_modules | grep -v '.test.' | grep -v '.d.ts')

# If running standalone (architect audit), scan all source files:
# SCAN_FILES=$(find src -name '*.ts' -o -name '*.tsx' | grep -v node_modules | grep -v '.test.' | grep -v '.d.ts')
```

If `SCAN_FILES` is empty, report "No source files to scan" and exit with PASS.

---

## Step 2: GOV-001 — Documentation Standard

**Checks:**
1. **Exported functions have JSDoc/TSDoc:** For each file in `SCAN_FILES`, search for `export function` or `export const ... =` and verify the line above contains `/**` (JSDoc block). Report files with undocumented exports.
2. **README exists:** Check that `README.md` exists in the repo root.

```bash
# Check for exported functions/consts missing JSDoc
for file in $SCAN_FILES; do
  # Get line numbers of exports
  grep -n "^export " "$file" | while read line; do
    LINENUM=$(echo "$line" | cut -d: -f1)
    PREV=$((LINENUM - 1))
    # Check if previous line ends a JSDoc block
    PREV_CONTENT=$(sed -n "${PREV}p" "$file")
    if ! echo "$PREV_CONTENT" | grep -q '[\*/]'; then
      echo "GOV-001 WARN: $file:$LINENUM — exported symbol missing JSDoc"
    fi
  done
done

# README check
if [ ! -f README.md ]; then
  echo "GOV-001 FAIL: README.md missing"
fi
```

**Result:** FAIL if README missing. WARN for missing JSDoc (advisory — some exports like type re-exports don't need JSDoc).

---

## Step 3: GOV-002 — Testing Protocol

**Checks:**
1. **Test file coverage:** Every new/modified `.ts`/`.tsx` source file in `src/` must have a corresponding `.test.ts`/`.test.tsx` file.
2. **No skipped tests:** Scan test files for `.skip` or `xit` or `xdescribe`.

```bash
# Test file mapping
for file in $SCAN_FILES; do
  if echo "$file" | grep -q "^src/"; then
    TEST_FILE=$(echo "$file" | sed 's/\.tsx\?$/.test.&/' | sed 's/\.test\.\./.test./')
    # Also check __tests__ directory pattern
    DIR=$(dirname "$file")
    BASE=$(basename "$file" | sed 's/\.tsx\?$//')
    ALT_TEST="$DIR/__tests__/$BASE.test.ts"
    if [ ! -f "$TEST_FILE" ] && [ ! -f "$ALT_TEST" ]; then
      echo "GOV-002 FAIL: $file has no test file (expected $TEST_FILE)"
    fi
  fi
done

# Skipped tests
grep -rn '\.skip\|xit(\|xdescribe(' src/ --include='*.test.*' && echo "GOV-002 WARN: Skipped tests found"
```

**Result:** FAIL if source files lack test files. WARN if skipped tests found.

---

## Step 4: GOV-003 — Coding Standard

**Checks:**
1. **No `any` type:** Scan for explicit `any` usage (`: any`, `as any`, `<any>`).
2. **No `console.log`:** Should use structured logging (pino) instead.
3. **Function length:** Warn if any function body exceeds 60 lines.
4. **TypeScript strict mode:** Verify `tsconfig.json` has `"strict": true`.

```bash
# any usage
for file in $SCAN_FILES; do
  MATCHES=$(grep -n ': any\b\|as any\b\|<any>' "$file" | grep -v '// eslint-disable' | grep -v '// GOV-003-exempt')
  if [ -n "$MATCHES" ]; then
    echo "GOV-003 FAIL: $file contains 'any' type usage:"
    echo "$MATCHES"
  fi
done

# console.log (not in test files)
for file in $SCAN_FILES; do
  if ! echo "$file" | grep -q '.test.'; then
    MATCHES=$(grep -n 'console\.\(log\|warn\|error\|debug\|info\)' "$file" | grep -v '// GOV-003-exempt')
    if [ -n "$MATCHES" ]; then
      echo "GOV-003 FAIL: $file uses console.* instead of pino logger:"
      echo "$MATCHES"
    fi
  fi
done

# TypeScript strict
if [ -f tsconfig.json ]; then
  if ! grep -q '"strict":\s*true\|"strict": true' tsconfig.json; then
    echo "GOV-003 FAIL: tsconfig.json missing strict: true"
  fi
fi
```

**Result:** FAIL on `any` usage or `console.*` in source files. FAIL if strict mode disabled.

---

## Step 5: GOV-004 — Error Handling Protocol

**Checks:**
1. **No raw `throw new Error()`:** Must use `ApplicationError` or framework-specific error class (e.g., `TRPCError`).
2. **No unhandled promise rejections:** Scan for `.then()` without `.catch()` (advisory).

```bash
# Raw throw new Error
for file in $SCAN_FILES; do
  if ! echo "$file" | grep -q '.test.'; then
    MATCHES=$(grep -n 'throw new Error(' "$file" | grep -v '// GOV-004-exempt')
    if [ -n "$MATCHES" ]; then
      echo "GOV-004 FAIL: $file uses raw 'throw new Error()' — use ApplicationError or TRPCError:"
      echo "$MATCHES"
    fi
  fi
done
```

**Result:** FAIL on raw `throw new Error()` in non-test files.

---

## Step 6: GOV-005 — Agentic Development Lifecycle

**Checks:**
1. **Branch naming:** Must match `feature/SPR-NNN-*` pattern (already in `/git_commit`).
2. **Commit message format:** Must match `type(scope): description` pattern.

```bash
# Branch check
BRANCH=$(git branch --show-current)
if [ -n "$BRANCH" ] && [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
  if ! echo "$BRANCH" | grep -qE '^(feature|fix|hotfix|deploy)/'; then
    echo "GOV-005 FAIL: Branch '$BRANCH' doesn't follow naming convention"
  fi
fi
```

**Result:** FAIL on bad branch name. Commit message checked by `/git_commit`.

---

## Step 7: GOV-006 — Logging Specification

**Checks:**
1. **Route files use pino:** Any file in `routes/` or `routers/` or `api/` must import a logger.
2. **No console.log:** (Already checked in GOV-003, but specific to logging context here.)

```bash
# Route/router files should import logger
for file in $SCAN_FILES; do
  if echo "$file" | grep -qE 'route|router|api/'; then
    if ! grep -q 'logger\|pino\|log\.' "$file"; then
      echo "GOV-006 WARN: $file is a route/router but doesn't import a logger"
    fi
  fi
done
```

**Result:** WARN if route files lack logger import.

---

## Step 8: GOV-008 — Infrastructure & Operations

**Checks:**
1. **`.env.example` exists:** If `.env` is used, `.env.example` must exist.
2. **New env vars documented:** If any file references `process.env.NEW_VAR`, check that `NEW_VAR` appears in `.env.example`.

```bash
# .env.example check
if [ -f .env ] || grep -rq 'process\.env\.' src/ 2>/dev/null; then
  if [ ! -f .env.example ]; then
    echo "GOV-008 FAIL: .env.example missing but process.env is used"
  else
    # Check for undocumented env vars
    for file in $SCAN_FILES; do
      grep -oP 'process\.env\.(\w+)' "$file" | sed 's/process\.env\.//' | sort -u | while read VAR; do
        if ! grep -q "$VAR" .env.example; then
          echo "GOV-008 WARN: $file references process.env.$VAR but it's not in .env.example"
        fi
      done
    done
  fi
fi
```

**Result:** FAIL if `.env.example` missing. WARN for undocumented env vars.

---

## Step 9: Summary Report

Print a summary table:

```
╔══════════════════════════════════════════════════╗
║          GOVERNANCE COMPLIANCE REPORT            ║
╠══════════╦═══════╦═══════════════════════════════╣
║ GOV-001  ║ PASS  ║ Documentation Standard        ║
║ GOV-002  ║ FAIL  ║ Missing test: src/lib/foo.ts   ║
║ GOV-003  ║ PASS  ║ Coding Standard               ║
║ GOV-004  ║ WARN  ║ 1 raw throw new Error()       ║
║ GOV-005  ║ PASS  ║ Branch naming OK              ║
║ GOV-006  ║ PASS  ║ Logging Specification         ║
║ GOV-007  ║ SKIP  ║ Manual check (sprint doc)     ║
║ GOV-008  ║ PASS  ║ Infrastructure & Operations   ║
╠══════════╩═══════╩═══════════════════════════════╣
║ RESULT: 1 FAIL — commit blocked                  ║
╚══════════════════════════════════════════════════╝
```

**Exit behavior:**
- Any FAIL → exit 1 (blocks commit when called from `/git_commit`)
- WARNings only → exit 0 with advisory messages
- All PASS → exit 0

---

## Step 10: Exempt Patterns

Some code legitimately needs `any` or `throw new Error`. Use inline comments to exempt:

```typescript
// GOV-003-exempt: third-party callback requires any
type Callback = (data: any) => void;

// GOV-004-exempt: base error class constructor
throw new Error('Unimplemented');
```

The scanner skips lines with `GOV-NNN-exempt` comments. Use sparingly — the Architect reviews all exemptions during audits.

---

## When Called From /git_commit

The `/git_commit` workflow calls this scan as Step 4 (after lint/typecheck/test, before commit):

```
Step 3: Quality gates (lint, typecheck, test)
Step 4: /governance_scan ← THIS WORKFLOW
Step 5: Commit
```

If the governance scan fails, the commit is blocked.
