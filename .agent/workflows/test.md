---
description: Universal test runner — auto-detect stack, run GOV-002 tiers, output forensic report
---
// turbo-all

## Overview

This workflow auto-detects the project's tech stack, runs GOV-002 test tiers in fail-fast
order, and outputs a forensic test report to `CODEX/40_VERIFICATION/`.

**Slash command variants:**

| Command | Behavior |
|:--|:--|
| `/test` | Run all applicable tiers (auto-detect) |
| `/test static` | Run only static analysis (Tier 1) |
| `/test unit` | Run only unit tests + coverage (Tier 2) |
| `/test coverage` | Run units + report coverage only |
| `/test --through integration` | Run tiers 1–6 |
| `/test --tier 7` | Run only a specific tier |
| `/test --safety` | Run all tiers with safety-critical thresholds (95%/90%/95%) |
| `/test report` | Generate report from last run without re-running |

---

## Step 1: Detect Tech Stack

Scan the project root to determine the primary language and framework:

```bash
echo "=== Stack Detection ==="
for f in pyproject.toml setup.py setup.cfg requirements.txt; do
  [ -f "$f" ] && echo "PYTHON:$f"
done
for f in package.json; do
  [ -f "$f" ] && echo "JAVASCRIPT:$f"
done
for f in go.mod; do
  [ -f "$f" ] && echo "GO:$f"
done
for f in Cargo.toml; do
  [ -f "$f" ] && echo "RUST:$f"
done
for f in CMakeLists.txt Makefile; do
  [ -f "$f" ] && echo "C_CPP:$f"
done
echo "=== End Detection ==="
```

Record the detected stack. If multiple are present, treat the project as polyglot and
run the appropriate tools for each detected language.

### Frontend Framework Detection (JavaScript/TypeScript only)

If `package.json` was detected, inspect it to determine the frontend framework:

```bash
if [ -f package.json ]; then
  echo "=== Frontend Detection ==="
  grep -l '"react"' package.json 2>/dev/null && echo "FRONTEND:react"
  grep -l '"vue"' package.json 2>/dev/null && echo "FRONTEND:vue"
  grep -l '"svelte"' package.json 2>/dev/null && echo "FRONTEND:svelte"
  grep -l '"@angular/core"' package.json 2>/dev/null && echo "FRONTEND:angular"
  echo "=== End Frontend Detection ==="
fi
```

---

## Step 2: Select Tool Chain

Based on the detected stack, select the tools for each tier. Use this matrix:

### Python
| Tier | Tool | Command |
|:--|:--|:--|
| Static: Lint | ruff | `ruff check . --output-format=text` |
| Static: Types | mypy | `mypy src/ --strict` |
| Static: Complexity | radon | `radon cc src/ -s -n C` |
| Static: Dead code | vulture | `vulture src/` |
| Static: Security | bandit | `bandit -r src/ -f json` |
| Static: Deps | pip-audit | `pip-audit` |
| Unit tests | pytest | `pytest tests/ -m "not integration and not e2e" -v --tb=short` |
| Coverage | coverage.py | `pytest --cov=src --cov-report=term-missing --cov-report=json` |
| Property tests | hypothesis | `pytest tests/ -m property -v` |
| Snapshot tests | syrupy | `pytest tests/ -m snapshot -v` |
| Mutation tests | mutmut | `mutmut run --paths-to-mutate=src/` |
| Integration tests | pytest | `pytest tests/ -m integration -v` |
| E2E tests | pytest | `pytest tests/ -m e2e -v` |
| Performance tests | pytest-benchmark | `pytest tests/ -m performance --benchmark-only` |

### JavaScript / TypeScript
| Tier | Tool | Command |
|:--|:--|:--|
| Static: Lint | eslint | `npx eslint . --format=json` |
| Static: Types (TS) | tsc | `npx tsc --noEmit` |
| Static: Security | npm audit | `npm audit --json` |
| Unit tests | jest or vitest | `npx jest --verbose` or `npx vitest run` |
| Coverage | c8 / istanbul | `npx jest --coverage` or `npx vitest run --coverage` |
| Property tests | fast-check | `npx jest --testPathPattern=property` |
| Snapshot tests | jest snapshots | `npx jest --testPathPattern=snapshot` |
| Mutation tests | stryker | `npx stryker run` |
| Integration tests | jest/vitest | `npx jest --testPathPattern=integration` |
| E2E tests | playwright | `npx playwright test` |
| GUI/Visual tests | playwright + axe | `npx playwright test --project=visual` |
| Accessibility | axe-core | `npx axe --dir src/` |
| Performance tests | lighthouse | `npx lighthouse --output=json` |

### Frontend-Specific Additions
| Framework | Component Tests | Visual Tests |
|:--|:--|:--|
| React | `@testing-library/react` | Playwright + Percy |
| Vue | `@vue/test-utils` | Playwright + Percy |
| Svelte | `@testing-library/svelte` | Playwright |
| Angular | `@angular/core/testing` | Playwright |

### Go
| Tier | Tool | Command |
|:--|:--|:--|
| Static: Vet | go vet | `go vet ./...` |
| Static: Lint | golangci-lint | `golangci-lint run` |
| Unit tests | go test | `go test ./... -v -short` |
| Coverage | go test | `go test ./... -coverprofile=coverage.out` |
| Integration tests | go test | `go test ./... -v -run Integration` |
| Performance tests | go test | `go test ./... -bench=. -benchmem` |

### Rust
| Tier | Tool | Command |
|:--|:--|:--|
| Static: Lint | clippy | `cargo clippy -- -D warnings` |
| Unit tests | cargo test | `cargo test --lib` |
| Coverage | tarpaulin | `cargo tarpaulin --out json` |
| Integration tests | cargo test | `cargo test --test '*'` |
| Performance tests | criterion | `cargo bench` |

### C/C++
| Tier | Tool | Command |
|:--|:--|:--|
| Static: Lint | cppcheck | `cppcheck --enable=all src/` |
| Static: Tidy | clang-tidy | `clang-tidy src/*.cpp` |
| Unit tests | ctest/gtest | `ctest --output-on-failure` |
| Coverage | gcov/llvm-cov | `gcov *.gcda` or `llvm-cov report` |

---

## Step 3: Execute Tiers (Fail-Fast)

Run each applicable tier **in GOV-002 order**. If any tier fails, **STOP** and report.
Only run tiers that have corresponding test files/config present.

### GOV-002 Execution Order:

1. **Static Analysis** — Run ALL static tools. Any failure = halt.
2. **Unit Tests** — Run unit tests + coverage. Check thresholds.
3. **Property-Based Tests** — Run if property test files exist.
4. **Snapshot Tests** — Run if snapshot test files exist.
5. **Mutation Tests** — Run if mutation testing is configured.
6. **Integration Tests** — Run if integration test files exist.
7. **Contract Tests** — Run if contract test files exist.
8. **Fuzz Tests** — Run if fuzz test files exist.
9. **E2E Tests** — Run if E2E test files exist.
10. **GUI/Visual Tests** — Run if frontend project with visual tests.
11. **Performance Tests** — Run if benchmark files exist. Fail on >10% regression.

### Tier Detection Heuristics

Before running each tier, check if it applies:

```bash
# Python tier detection
echo "=== Tier Availability ==="
find tests/ -name "test_*.py" -not -path "*/integration/*" -not -path "*/e2e/*" | head -1 | xargs -I{} echo "TIER_UNIT:available"
grep -rl "@given\|@example\|hypothesis" tests/ 2>/dev/null | head -1 | xargs -I{} echo "TIER_PROPERTY:available"
grep -rl "snapshot\|syrupy" tests/ 2>/dev/null | head -1 | xargs -I{} echo "TIER_SNAPSHOT:available"
[ -f mutmut_config.py ] || [ -f setup.cfg ] && grep -q mutmut setup.cfg 2>/dev/null && echo "TIER_MUTATION:available"
find tests/ -path "*/integration/*" -name "*.py" | head -1 | xargs -I{} echo "TIER_INTEGRATION:available"
find tests/ -path "*/e2e/*" -name "*.py" | head -1 | xargs -I{} echo "TIER_E2E:available"
find tests/ -name "*benchmark*" -o -name "*perf*" | head -1 | xargs -I{} echo "TIER_PERFORMANCE:available"
echo "=== End Availability ==="
```

---

## Step 4: Check Coverage Thresholds

After running unit tests, check coverage against GOV-002 §20 thresholds:

### Standard Thresholds (default)
| Metric | Minimum | Action if below |
|:--|:--|:--|
| Line coverage | ≥80% | ❌ FAIL |
| Branch coverage | ≥75% | ❌ FAIL |
| Function coverage | 100% public | ⚠️ WARN |
| Assertion density | ≥2 per test | ⚠️ WARN |

### Safety-Critical Thresholds (`/test --safety`)
| Metric | Minimum | Action if below |
|:--|:--|:--|
| Line coverage | ≥95% | ❌ FAIL |
| Branch coverage | ≥90% | ❌ FAIL |
| Mutation score | ≥95% | ❌ FAIL |
| Function coverage | 100% all | ❌ FAIL |
| Assertion density | ≥3 per test | ❌ FAIL |
| MC/DC coverage | Required | ❌ FAIL |

### Coverage Extraction

**Python:**
```bash
# Run with JSON coverage output
pytest --cov=src --cov-report=json --cov-report=term-missing
# Parse coverage.json for line/branch percentages
python3 -c "import json; d=json.load(open('coverage.json')); print(f'LINE:{d[\"totals\"][\"percent_covered\"]:.1f}%'); print(f'BRANCH:{d[\"totals\"].get(\"percent_covered_branches\", \"N/A\")}')"
```

**JavaScript:**
```bash
# Jest outputs coverage to coverage/coverage-summary.json
npx jest --coverage --coverageReporters=json-summary
cat coverage/coverage-summary.json | python3 -c "import json,sys; d=json.load(sys.stdin)['total']; print(f'LINE:{d[\"lines\"][\"pct\"]}%'); print(f'BRANCH:{d[\"branches\"][\"pct\"]}%')"
```

---

## Step 5: Generate Forensic Report

After all tiers complete (or on first failure), generate the master report.

Create or overwrite `CODEX/40_VERIFICATION/VER-TEST-REPORT_latest.md` with this structure:

```markdown
---
id: VER-TEST-REPORT
title: "Test Report"
type: report
status: {PASS or FAIL}
created: {ISO date}
tags: [testing, verification, automated]
related: [GOV-002]
---

# Test Report — {project_name}

| Field | Value |
|:--|:--|
| Timestamp | {ISO 8601 with timezone} |
| Git Commit | {short SHA from `git rev-parse --short HEAD`} |
| Branch | {from `git branch --show-current`} |
| Tech Stack | {detected language + framework} |
| Mode | {standard / safety-critical} |

## Tier Results

| # | Tier | Status | Duration | Details |
|:--|:--|:--|:--|:--|
| 1 | Static Analysis | ✅/❌/⏭️ | Xs | {tool count, warning count} |
| 2 | Unit Tests | ✅/❌/⏭️ | Xs | {pass/fail/skip counts} |
| 3 | Property Tests | ✅/❌/⏭️ | Xs | {examples tested} |
| 4 | Snapshot Tests | ✅/❌/⏭️ | Xs | {matched/updated/new} |
| 5 | Mutation Tests | ✅/❌/⏭️ | Xs | {killed/survived/total} |
| 6 | Integration Tests | ✅/❌/⏭️ | Xs | {pass/fail counts} |
| 7 | Contract Tests | ✅/❌/⏭️ | Xs | {verified/broken} |
| 8 | Fuzz Tests | ✅/❌/⏭️ | Xs | {inputs tested} |
| 9 | E2E Tests | ✅/❌/⏭️ | Xs | {scenarios passed} |
| 10 | GUI/Visual Tests | ✅/❌/⏭️ | Xs | {visual diffs, a11y issues} |
| 11 | Performance Tests | ✅/❌/⏭️ | Xs | {regression %} |

Legend: ✅ Pass | ❌ Fail | ⏭️ Skipped (not applicable or blocked by prior failure)

## Coverage Summary

| Metric | Value | Threshold | Status |
|:--|:--|:--|:--|
| Line coverage | X% | ≥80% | ✅/❌ |
| Branch coverage | X% | ≥75% | ✅/❌ |
| Function coverage | X% | 100% public | ✅/❌ |
| Mutation score | X% | ≥80% | ✅/❌ |
| Assertion density | X/test | ≥2 | ✅/❌ |

## Failures

{For each failed tier:}
### Tier N: {Name} — ❌ FAIL

**Tool**: {tool name}
**Error**:
\```
{error output, truncated to key lines}
\```
**Fix hint**: {actionable suggestion}

## Verdict: ✅ PASS / ❌ FAIL

{If FAIL: "Fix Tier {first_failing_tier} first. GOV-002 §18: subsequent tiers skipped."}
{If PASS: "All {N} applicable tiers passed. Coverage meets {standard/safety-critical} thresholds."}
```

---

## Step 6: Present Results

After the report is generated:

1. Print a **summary table** to the user showing tier results
2. Highlight any **failures** with the specific error and a fix suggestion
3. Show the **coverage numbers** vs thresholds
4. Link to the full report: `CODEX/40_VERIFICATION/VER-TEST-REPORT_latest.md`
5. If all tiers passed, congratulate and note any optional tiers that were skipped
6. If a tier failed, remind them: *"GOV-002 §18: Fix the fastest-failing tier first"*

---

## Troubleshooting

### "No tests found"
- Check that test files follow naming conventions (`test_*.py`, `*.test.js`, `*_test.go`)
- Check that pytest markers are configured (see GOV-002 §25 step 5)

### "Tool not installed"
- Python: `pip install ruff mypy radon vulture bandit pip-audit pytest-cov hypothesis mutmut`
- JavaScript: `npm install -D eslint jest @testing-library/react playwright axe-core`
- Go: `go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest`

### Coverage below threshold
- Check for untested public functions: `coverage report --show-missing`
- Add boundary and error-path tests for uncovered branches (GOV-002 §4)

### Mutation score too low
- Mutation survivors indicate weak assertions — add assertions that verify specific values, not just truthiness
- Target: every mutation should be caught by at least one test
