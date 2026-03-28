---
description: Run tests, analyze failures, fix issues, re-run until all pass. Zero tolerance for skips.
---

# VoxInput Test Fix Workflow

> **ZERO SKIPS**: All tests MUST pass. Fix the underlying issue — never skip a test.

## 1. System Prep
First, reset the environment to a clean state.

### A. Kill Stale Processes
// turbo
```bash
pkill -f "VoxInput/run.py" 2>/dev/null
pkill -f "python.*VoxInput" 2>/dev/null
pkill -f "python.*pytest" 2>/dev/null
sleep 2 && echo "Stale processes killed"
```

### B. Verify Resources
// turbo
```bash
echo "=== Memory ===" && free -h | head -3
echo "=== Python ===" && pgrep -af python 2>/dev/null || echo "None running"
```

### C. Clear Test Artifacts
// turbo
```bash
PROJ="$(git -C ~/Documents/VoxInput rev-parse --show-toplevel)"
rm -rf "$PROJ/.pytest_cache" "$PROJ/reports" "$PROJ/htmlcov" 2>/dev/null
rm -f "$PROJ"/*.log "$PROJ"/src/*.pyc 2>/dev/null
find "$PROJ" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo "Artifacts cleared"
```

---

## 2. Static Analysis

### A. Syntax Check (changed files only)
// turbo
```bash
cd ~/Documents/VoxInput && source venv/bin/activate
git diff --name-only HEAD -- '*.py' | xargs -r python -m py_compile && echo "✅ Syntax OK"
```

### B. Ruff Lint (if installed)
```bash
cd ~/Documents/VoxInput && source venv/bin/activate
ruff check src/ tests/ --select E,W,F --ignore E501 2>/dev/null || echo "ruff not installed, skipping"
```

---

## 3. Test Execution Loop

Run tests, analyze failures, fix, repeat until Exit Code 0.

### Step A: Run Unit Tests
// turbo
```bash
cd ~/Documents/VoxInput && source venv/bin/activate
python -m pytest tests/unit -q --tb=short 2>&1 | tail -30
```

### Step B: Run Integration Tests (if they exist)
```bash
cd ~/Documents/VoxInput && source venv/bin/activate
python -m pytest tests/integration -q --tb=short 2>&1 | tail -30
```

### Step C: Analyze Failures
If ANY tests fail:
1. Read the failure traceback — exact test name, exception, file:line
2. Identify root cause: stale mock? API change? logic bug?
3. Apply fix
4. **REPEAT from Step A** — run the specific failing test first:
   ```bash
   python -m pytest tests/unit/test_<FILE>.py::<TestClass>::<test_name> -v --tb=long
   ```

---

## 4. WER Accuracy Test (Optional — Heavy)

> **WARNING**: Requires ~4GB free RAM. Do NOT run while VoxInput app is running.

```bash
cd ~/Documents/VoxInput && source venv/bin/activate
pkill -f "VoxInput/run.py" 2>/dev/null; sleep 2
timeout 120 python -u tools/wer_paragraph.py
```

---

## 5. Success Criteria

**DO NOT STOP** until:
1. `pytest` returns **Exit Code 0**
2. **0 failures**, **0 errors**, **0 skips**
3. All warnings investigated (deprecation warnings = future breakage)

Once green: restart VoxInput if needed, then commit via `/git-commit`.
