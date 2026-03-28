---
description: Mandatory rules for running shell commands safely without hanging. ALL agents must follow these rules for every command.
---

# Safe Command Execution — Anti-Hang Rules

> **ALL agents MUST follow these rules.** Violations cause zombie processes that block the system.

## Rule 1: NEVER Walk the Full Repo Tree

The DarkGravity project has heavy directories (`.venv`, `.git`, `__pycache__`, `.darkgravity/embeddings/`). Walking them causes multi-minute hangs.

**❌ BANNED:**
```bash
# Never do this — hangs for 10+ minutes
find . -name "*.py" -exec python3 -c "..." {} \;
python3 -c "for root, dirs, files in os.walk('.')..."
ruff check .
```

**✅ REQUIRED: Scope to changed files or specific directories:**
```bash
# Use git to get only the files you care about
git diff --name-only HEAD~1 -- '*.py' | xargs python3 -m py_compile
git diff --name-only main -- '*.py' | xargs -I{} ruff check {}

# Or scope to specific directories
ruff check src/darkgravity/engine/
python3 -m py_compile src/darkgravity/engine/llm.py
```

## Rule 2: Set GIT_TERMINAL_PROMPT=0 for All Git Network Commands

Prevents git from ever blocking on an interactive credential/passphrase prompt.

```bash
# Always prefix git network commands:
GIT_TERMINAL_PROMPT=0 git fetch origin
GIT_TERMINAL_PROMPT=0 git push origin main
GIT_TERMINAL_PROMPT=0 git pull origin main
```

Local-only git commands (status, log, diff, branch, merge, commit) don't need this.

## Rule 3: Use Reasonable WaitMsBeforeAsync Values

| Command type | WaitMsBeforeAsync |
|---|---|
| `git status`, `git log`, `git branch` | 3000 |
| `git fetch`, `git push`, `git pull` | 10000 |
| `python3 -m py_compile <file>` | 5000 |
| `python3 -c "import ast; ..."` (AST check) | 5000 |
| `pytest` (single file) | 10000 |
| `pytest` (full suite) | 10000 (will go async) |
| Any `os.walk` or `find` on repo root | **BANNED** |
| `.venv/bin/python3 -c "import darkgravity..."` | 10000 (heavy imports) |

## Rule 4: Kill Before Re-running

If a command hung and you need to retry, **always kill the old one first**:
```
send_command_input(CommandId=..., Terminate=true)
```
Then wait before retrying. Never leave zombie processes.

## Rule 5: Syntax Checking — Use AST Parse, Not Imports

DarkGravity imports are HEAVY (litellm, tree-sitter, chromadb). Use `ast.parse()` instead:

```bash
# ✅ FAST: AST parse (no imports, instant)
python3 -c "import ast; ast.parse(open('src/darkgravity/engine/llm.py').read()); print('OK')"

# ❌ SLOW: Import (loads litellm, tree-sitter, etc — takes 60+ seconds)
.venv/bin/python3 -c "from darkgravity.engine.llm import LLMClient"
```

## Rule 6: Use fd/ripgrep Instead of find/grep

```bash
# Use fd (respects .gitignore, skips .venv/.git automatically)
fd -e py --max-depth 3 src/ | xargs python3 -m py_compile

# Use rg instead of grep
rg "some_pattern" src/darkgravity/engine/
```

## Rule 7: NEVER Poll command_status More Than Twice

The terminal metadata can show commands as "running" even after completion. This is a **phantom hang**.

**❌ BANNED:**
```
command_status(id, wait=30)  → "RUNNING" 
command_status(id, wait=60)  → "RUNNING"
command_status(id, wait=120) → "RUNNING"  ← you are stuck in a loop!
```

**✅ REQUIRED: Max 2 polls, then verify directly:**
```
command_status(id, wait=10)  → "RUNNING, no output"
command_status(id, wait=15)  → "RUNNING, no output"
# STOP POLLING. Run a new verification command:
run_command("git log --oneline -1")   # Did the commit happen?
run_command("python3 -c 'import ast; ...'")  # Does it compile?
```

## Rule 8: Verify Outcomes, Don't Trust Process Status

Always verify the **result** of an operation rather than its **process status**:

| Instead of checking... | Verify by running... |
|---|---|
| "Is git commit still running?" | `git log --oneline -1` |
| "Did the file compile?" | `python3 -c "import ast; ast.parse(open('file').read())"` |
| "Did tests pass?" | Check the test report or re-run a single test |
| "Is the module importable?" | `python3 -c "import ast; ast.parse(...)"` (NOT `import`) |
