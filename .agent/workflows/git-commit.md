---
description: Intelligent Git commit workflow — verify hygiene, analyze diffs, commit with detailed messages, push to GitHub.
---

1. **PROJECT ROOT VERIFICATION (CRITICAL)**
   - **ALWAYS** navigate to the repository root before running any git commands.
   - Run `git rev-parse --show-toplevel` to find the root.
   - **Reason**: Running `git add .` from a subdirectory misses files.

2. Check Status & Hygiene
   - Run `git status`.
   - **JUNK FILE CHECK**: Verify none of these are in the changelist:
     - `*.log`, `*.zip`, `*.pyc`, `startup_trace.log`, `strace.out`
     - `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
     - `*.db-wal`, `*.db-shm` (SQLite runtime files)
     - `/tmp/`, `reports/`, `logs/`
   - **ACTION FOR JUNK**:
     - Untracked: Add patterns to `.gitignore` then proceed.
     - Modified: `git restore <path>` to discard.
     - Staged: `git reset HEAD <path>` to unstage.
     - **NEVER COMMIT** runtime/test artifacts.

3. Update .gitignore (if needed)
   - If new artifact patterns were found, append to `.gitignore`.
   - Commit .gitignore update first as separate commit: `chore: update .gitignore`

4. Analyze Changes
   - Run `git diff` (unstaged) and `git diff --cached` (staged).
   - Read changes to understand the "Why" and "What."

// turbo-all
5. Execute Commit(s)
   - Stage: `git add -A`
   - Construct conventional commit message:
     ```
     type(scope): summary

     - detailed bullet point 1
     - detailed bullet point 2
     ```
   - `git commit -m "type(scope): summary" -m "- detail 1" -m "- detail 2"`

6. Push to GitHub
   - `GIT_TERMINAL_PROMPT=0 git push VoxInput main`
   - If push fails (upstream changes): `git pull --rebase VoxInput main` then retry.

7. Final Verify
   - `git status` — confirm clean working tree.
   - `git log -1` — confirm commit landed.
