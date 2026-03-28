---
description: Intelligent Git commit workflow — verify hygiene, analyze diffs, commit with detailed messages, and optionally push. Incorporates safe command execution rules.
---

# /git_commit

> Commit changes cleanly with full hygiene checks, intelligent commit messages, and safe command execution.

## Step 0: Safe Command Rules (READ FIRST)

> These rules apply to ALL commands in this workflow. Violations cause zombie processes.

- **`GIT_TERMINAL_PROMPT=0`** — Prefix ALL git network commands (`push`, `pull`, `fetch`) to prevent interactive credential hangs.
- **Never poll `command_status` more than twice** — If still "RUNNING" after 2 checks, verify the outcome directly (e.g., `git log -1`) instead of polling again.
- **Verify outcomes, not process status**:
  | Instead of checking... | Verify by running... |
  |---|---|
  | "Did git commit finish?" | `git log --oneline -1` |
  | "Did the push work?" | `GIT_TERMINAL_PROMPT=0 git log --oneline origin/main..HEAD` |
  | "Is the tree clean?" | `git status --porcelain` |
- **Use `fd`/`rg` over `find`/`grep`** — They respect `.gitignore` and skip `.venv/.git` automatically.
- **Never walk the full repo tree** — Scope to specific directories or use `git diff --name-only`.
- **`--no-verify` bypass** — If a pre-commit hook blocks a commit and the architect explicitly approves bypassing: `git commit --no-verify -m "..."`. Log the bypass reason in the commit body.

---

// turbo
## Step 1: Project Root Verification (CRITICAL)

**ALWAYS** verify you are at the repository root before running any git commands.

```bash
git rev-parse --show-toplevel
```

If the output does not match your expected project root, navigate there first.

**Reason**: Running `git add .` from a subdirectory silently misses changes in other directories.

---

## Step 2: Check Status & Hygiene

```bash
git status
```

### 2a. Run Compliance Gate

If the project has an active compliance engine hook, run it **before** reviewing the diff:

```bash
# Run the compliance check on staged files
bash bin/compliance_check.sh
```

If the compliance script fails, **STOP**. Resolve the errors (e.g., missing tags, exposed secrets) before continuing.

### 2b. Junk File Check

Verify NONE of these patterns appear in the changelist:

| Pattern | Why |
|:--------|:----|
| `*.log`, `*.pyc`, `*.pyo` | Runtime artifacts |
| `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Tool caches |
| `*.db-wal`, `*.db-shm` | SQLite runtime files (WAL/shared memory) |
| `*.egg-info/`, `dist/`, `build/` | Build artifacts |
| `/tmp/`, `tmp/`, `.tmp/` | Temp files |
| `*.svg`, `*.zip` (unless intentional assets) | Binary artifacts |
| `logs/`, `**/logs/`, `reports/` | Ephemeral output |
| `strace.out`, `startup_trace.log` | Debug traces |
| `.env`, `*.pem`, `*.key`, `*secret*`, `*credential*` | **Secrets / credentials** |

### 2b. Secret & Credential Scan — BLOCKING

> [!CAUTION]
> This gate BLOCKS the commit if secrets are detected. No exceptions.

Before any commit, scan staged files for exposed secrets:

```bash
# Scan staged files for secret patterns
SECRET_HITS=$(git diff --cached --name-only | xargs grep -l -i -E \
  '(api[_-]?key|password|secret[_-]?key|private[_-]?key|credential)[[:space:]]*[=:][[:space:]]*["\x27]' \
  2>/dev/null || true)

# Also scan for known secret formats (API keys, tokens, PEM blocks)
FORMAT_HITS=$(git diff --cached -U0 | grep -E \
  '^\+.*(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9]{20}|xox[bpas]-[a-zA-Z0-9-]{20,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)' \
  2>/dev/null || true)

if [ -n "$SECRET_HITS" ] || [ -n "$FORMAT_HITS" ]; then
  echo "❌ SECRET LEAK DETECTED — commit BLOCKED"
  [ -n "$SECRET_HITS" ] && echo "Files with secret patterns:" && echo "$SECRET_HITS" | sed 's/^/  /'
  [ -n "$FORMAT_HITS" ] && echo "Staged diffs containing secret formats:" && echo "$FORMAT_HITS" | sed 's/^/  /'
  echo ""
  echo "Remove secrets and use environment variables instead."
  echo "If false positive, verify manually and document in commit message."
  exit 1
fi
echo "✅ No secrets detected"
```

**Common false positives** (OK to proceed after manual review):
- Variable names like `apiKey` or `secretKey` with no value assigned
- Documentation examples with placeholder values
- Test fixtures with fake values like `test-secret-key`

**Always blocked** (no override):
- `.env` files with real values
- `*.pem`, `*.key` files
- `keys/` directory contents
- Hardcoded passwords in scripts

### 2c. Test Artifact Check

Identify any test-generated files:
- `tests/artifacts/`, `**/test_artifacts/`
- Screenshots, recordings, or output files from test runs
- Database files in test directories: `*.db`, `*.sqlite`

### 2d. Pre-Commit Quality Gate (GOV-002, GOV-003, GOV-005, GOV-008)

> [!IMPORTANT]
> These gates are **mandatory**. Do NOT bypass them without explicit Architect approval.

**Branch name check (GOV-005):**

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"
```

- If on `main` → STOP unless you are the Architect Agent committing governance docs.
- Developer agents MUST be on a branch matching `feature/SPR-NNN-*` (one branch per sprint — GOV-005 §5.1).
- Do NOT create per-task branches (e.g., `feature/SPR-004-T034-*`). Use one branch per sprint with granular commits.

**CODEX submodule freshness (GOV-008):**

```bash
# Check if submodule is behind remote
git submodule status codex 2>/dev/null || git submodule status lexflow-codex 2>/dev/null
```

- If the submodule pointer is behind remote, run `git submodule update --remote` first.
- Working against stale governance docs is a compliance violation.

**Test / lint / typecheck gate (GOV-002, GOV-003):**

```bash
# Run all quality checks (Node.js projects)
if [ -f package.json ]; then
  npm run lint 2>&1       || { echo "❌ LINT FAILED — fix before committing"; exit 1; }
  npm run typecheck 2>&1  || { echo "❌ TYPECHECK FAILED — fix before committing"; exit 1; }
  npm run test 2>&1       || { echo "❌ TESTS FAILED — fix before committing"; exit 1; }
  echo "✅ All quality gates passed"
fi
```

- **ALL THREE** must pass before any commit.
- Do NOT use `--no-verify` to bypass test failures — fix the code.
- If a test is flaky, document it in a `DEF-` report and fix the test, don't skip it.

**Test coverage check (GOV-002) — CRITICAL:**

> [!CAUTION]
> "Existing tests pass" is NOT sufficient. New source files MUST have test files.

For every new or modified `.ts` file in `src/`, verify a corresponding `.test.ts` file exists:

```bash
# Check that new/modified source files have corresponding test files
MISSING_TESTS=""
for src_file in $(git diff --cached --name-only --diff-filter=ACM | grep '^src/.*\.ts$' | grep -v '\.test\.' | grep -v '\.spec\.' | grep -v '\.d\.ts$'); do
  test_file="${src_file%.ts}.test.ts"
  if [ ! -f "$test_file" ]; then
    MISSING_TESTS="${MISSING_TESTS}\n  ❌ ${src_file} → missing ${test_file}"
  fi
done

if [ -n "$MISSING_TESTS" ]; then
  echo "❌ TEST COVERAGE VIOLATION (GOV-002)"
  echo "The following source files have no corresponding test file:"
  echo -e "$MISSING_TESTS"
  echo ""
  echo "Every new source file MUST have a test file. This is not optional."
  echo "STOP — write the tests before committing."
  exit 1
fi
```

**Exclusions** — these file types do NOT require test files:
- `src/db/schema.ts` (schema definitions — tested via integration)
- `src/**/index.ts` (barrel exports)
- `src/**/*.d.ts` (type declarations)
- Config files (`drizzle.config.ts`, `vitest.config.ts`)

If a file genuinely doesn't need its own test file, the agent must explain why in the commit message body.

**Governance scan (ALL 8 GOV docs) — BLOCKING:**

> [!CAUTION]
> This scan runs the `/governance_scan` workflow against all staged source files.
> Any FAIL result blocks the commit. Fix violations before proceeding.

Run the `/governance_scan` workflow now. It checks:
- **GOV-001**: Exported functions have JSDoc/TSDoc, README exists
- **GOV-003**: No `any` types, no `console.log` in source files, TypeScript strict mode
- **GOV-004**: No raw `throw new Error()` — use `ApplicationError` or `TRPCError`
- **GOV-006**: Route/router files import a logger
- **GOV-008**: `.env.example` exists if `process.env` is used, all env vars documented

Lines with `// GOV-NNN-exempt` comments are excluded from checks.

If any check returns FAIL → STOP. Fix the violations before committing.

### 2e. Action for Junk

| Found in... | Action |
|:------------|:-------|
| Untracked files | Add patterns to `.gitignore`, then proceed |
| Modified files | `git restore <path>` to discard changes |
| Staged files | `git reset HEAD <path>` to unstage |

**NEVER COMMIT** runtime artifacts, test output, secrets, or ephemeral databases.

---

## Step 3: Update .gitignore (if needed)

If new junk patterns were identified in Step 2, append them to `.gitignore`.

**Commit .gitignore first as a separate commit:**

```bash
git add .gitignore
git commit -m "chore: update .gitignore"
```

---

## Step 4: Analyze Changes

Start with the high-level summary, then drill into details:

```bash
git diff --stat                    # Summary: which files, how many lines
git diff                           # Full unstaged changes
git diff --cached                  # Full staged changes
```

**What to determine from the diff:**
1. **Why** — What motivated these changes? (bug fix, feature, refactor)
2. **What** — What specifically changed?
3. **Scope** — Are these changes ONE concern, or multiple unrelated concerns?
4. **Breaking changes** — Do any changes break backwards compatibility?

> [!IMPORTANT]
> **Single-concern commits**: If the diff spans multiple unrelated concerns (e.g., a bug fix AND a new feature AND a refactor), split them into separate commits in Step 5.

---

// turbo-all
## Step 5: Stage & Commit

### 5a. Staging Strategy

- **Single concern** → `git add -A` (stages everything)
- **Multiple concerns** → Stage and commit separately:
  ```bash
  git add src/engine/              # Stage only engine changes
  git commit -m "feat(engine): add retry logic"
  git add tests/                   # Stage only test changes
  git commit -m "test(engine): add retry logic tests"
  ```

### 5b. Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/) with **structured fields for agent parsing**:

```
type(scope): summary (imperative mood, ≤72 chars)

Why: [motivation — what problem or goal drove this change]
What: [1-2 sentence description of the actual change]
Files: [key files touched, comma-separated]
Agent: [architect | coder | tester | researcher | deployer]
Refs: [CODEX doc IDs if applicable — DEF-003, EVO-012]

BREAKING CHANGE: [if applicable]
```

**Example:**
```bash
git commit -m "feat(auth): add JWT token refresh endpoint" \
  -m "Why: Session tokens expired after 15 min causing agent workflow interruptions" \
  -m "What: Added /auth/refresh endpoint with sliding window expiration" \
  -m "Files: src/auth/routes.py, src/auth/tokens.py, tests/test_auth.py" \
  -m "Agent: coder" \
  -m "Refs: DEF-012, BLU-005"
```

**Field requirements:**

| Field | Required | Purpose |
|:------|:---------|:--------|
| `type(scope): summary` | **Mandatory** | Categorize and filter commits programmatically |
| `Agent:` | **Mandatory** | Provenance — which agent role made this change |
| `Why:` | Recommended | Motivation without reading the diff |
| `What:` | Recommended | Specific change description |
| `Files:` | Recommended | Key files without running `git show --stat` |
| `Refs:` | When applicable | Traceability to CODEX docs (DEF, EVO, BLU, etc.) |
| `BREAKING CHANGE:` | When applicable | Backwards compatibility breaks |

**Types:**

| Type | When |
|:-----|:-----|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or modifying tests |
| `docs` | Documentation only |
| `chore` | Maintenance, dependencies, tooling |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |
| `style` | Formatting, whitespace (no logic change) |

**Breaking changes** — Use `!` after type/scope:
```bash
git commit -m "feat(api)!: change response format to v2" \
  -m "Why: v1 response format limited pagination support" \
  -m "BREAKING CHANGE: response field 'data' renamed to 'payload'" \
  -m "Agent: coder" \
  -m "Refs: EVO-008"
```

### 5c. Commit Quality Checklist

Before executing the commit, verify:
- [ ] Subject line is in **imperative mood** ("add feature" not "added feature")
- [ ] Subject line is ≤72 characters
- [ ] `Agent:` field is present
- [ ] `Why:` explains motivation, not just restates the diff
- [ ] Breaking changes flagged with `!` and `BREAKING CHANGE:` footer
- [ ] Each commit addresses **one logical change**
- [ ] `Refs:` links to CODEX doc IDs if the change relates to a documented defect, feature, or spec

---

## Step 6: Push to Remote (optional)

Only push when the architect requests it, or if the workflow explicitly calls for it.

```bash
GIT_TERMINAL_PROMPT=0 git push origin main
```

**If push is rejected** (upstream has new commits):

```bash
# Stash any uncommitted work first (safety)
git stash --include-untracked

# Rebase onto upstream
GIT_TERMINAL_PROMPT=0 git pull --rebase origin main

# Restore stashed work (if any)
git stash pop 2>/dev/null

# Retry push
GIT_TERMINAL_PROMPT=0 git push origin main
```

**If rebase has conflicts**:
1. Report the conflicting files to the architect
2. Do NOT auto-resolve — wait for instruction

> [!IMPORTANT]
> Always use `GIT_TERMINAL_PROMPT=0` to prevent interactive credential hangs.

---

## Step 7: Final Verification

```bash
git status                # Confirm clean working tree
git log --oneline -3      # Confirm recent commits
```

- If untracked files remain that should be ignored → add to `.gitignore` and commit again.
- If `git status` shows a clean tree and `git log` shows your commit(s) → **done**.

---

## Quick Reference

| Scenario | Command |
|:---------|:--------|
| Stage everything | `git add -A` |
| Stage selectively | `git add <path>` |
| Unstage a file | `git reset HEAD <path>` |
| Discard changes | `git restore <path>` |
| Bypass hooks (with architect approval) | `git commit --no-verify -m "..."` |
| Check for secrets | `git diff --cached --name-only \| xargs grep -l -i -E '(api_key\|password\|secret\|token)'` |
| View commit summary | `git log --oneline -5` |
| Diff summary | `git diff --stat` |
