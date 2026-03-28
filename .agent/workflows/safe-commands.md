---
description: Mandatory rules for running shell commands safely without hanging. ALL agents must follow these rules.
---

# Safe Command Execution — Anti-Hang Rules

> **ALL agents MUST follow these rules.** Violations cause zombie processes.

## Rule 1: Set GIT_TERMINAL_PROMPT=0 for Network Git

Prevents git from blocking on credential/passphrase prompts.

```bash
GIT_TERMINAL_PROMPT=0 git push origin main
GIT_TERMINAL_PROMPT=0 git pull origin main
```

Local git commands (status, log, diff, commit) don't need this.

## Rule 2: Reasonable WaitMsBeforeAsync Values

| Command type | WaitMsBeforeAsync |
|---|---|
| `git status`, `git log`, `git diff` | 3000 |
| `git push`, `git pull` | 10000 |
| `python -m pytest tests/unit` (single file) | 10000 |
| `python -m pytest tests/unit` (full suite) | 10000 (goes async) |
| VoxInput start (`python run.py`) | 500 (always async) |
| `pkill` / `kill` commands | 3000 |

## Rule 3: Kill Before Re-running

If a command hung, **always kill the old one first**:
```
send_command_input(CommandId=..., Terminate=true)
```
Never leave zombie processes.

## Rule 4: NEVER Poll command_status More Than Twice

```
# Max 2 polls. If still "RUNNING" with no output → stop polling.
# Run a fresh verification command instead:
git log --oneline -1       # Did the commit happen?
git status --short         # Is the tree clean?
pgrep -af "VoxInput"       # Is VoxInput running?
```

## Rule 5: VoxInput-Specific

- **Never run VoxInput synchronously** — it blocks forever (GTK main loop).
  Always use `nohup python run.py > startup_trace.log 2>&1 & disown`.
- **Never run WER tests while VoxInput is running** — the gigaspeech model
  needs ~2.3GB RAM; two copies will hang the 32GB host.
- **Always use `/reset-environment` before test runs** to ensure clean state.
