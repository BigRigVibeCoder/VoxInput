---
description: One-time bootstrap — locate or clone DarkGravity, create venv, configure API keys
---
// turbo-all

## Prerequisites

- Python 3.11+ installed
- Git installed
- A Google AI Studio API key (free at https://aistudio.google.com/apikey)

## Steps

1. Try to auto-discover an existing DarkGravity installation:
```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "$PROJECT_ROOT/bin/resolve_darkgravity.sh" 2>/dev/null \
  && echo "FOUND: $DARKGRAVITY_HOME" || echo "NOT_FOUND"
```

If `FOUND`: skip to step 5 (save config). Otherwise continue with step 2.

2. Determine where to clone DarkGravity. Ask the user where they want it, or use the
   sibling-directory default (next to this project):
```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DARKGRAVITY_HOME="$(dirname "$PROJECT_ROOT")/darkgravity"
echo "Will clone to: $DARKGRAVITY_HOME"
```

3. Clone the DarkGravity repository:
```bash
git clone https://github.com/BigRigVibeCoder/darkgravity.git "$DARKGRAVITY_HOME"
```

4. Create the virtual environment and install dependencies:
```bash
python3 -m venv "$DARKGRAVITY_HOME/.venv"
"$DARKGRAVITY_HOME/.venv/bin/pip" install --upgrade pip
"$DARKGRAVITY_HOME/.venv/bin/pip" install -e "$DARKGRAVITY_HOME"
```

**(Optional)** Install web search extras for the `--web-search` flag:
```bash
"$DARKGRAVITY_HOME/.venv/bin/pip" install -e "$DARKGRAVITY_HOME[web]"
```

5. Save the engine path to the local config file (this is what all other workflows read):
```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir -p "$PROJECT_ROOT/.agent"
echo "DARKGRAVITY_HOME=$DARKGRAVITY_HOME" > "$PROJECT_ROOT/.agent/darkgravity.conf"
echo "Saved: $PROJECT_ROOT/.agent/darkgravity.conf"
cat "$PROJECT_ROOT/.agent/darkgravity.conf"
```

6. Configure API keys. Ask the user for their Google AI Studio API key, then write it:
```bash
cat > "$DARKGRAVITY_HOME/.env" << 'EOF'
# DarkGravity API Keys
# Required: Google AI Studio (free tier)
DG_GOOGLE_AI_API_KEY=REPLACE_WITH_USER_KEY

# Optional: OpenRouter (paid fallback)
# DG_OPENROUTER_API_KEY=sk-or-v1-...
EOF
```

**IMPORTANT**: Replace `REPLACE_WITH_USER_KEY` with the actual key provided by the user.

7. Verify the installation:
```bash
"$DARKGRAVITY_HOME/.venv/bin/python3" -c "from darkgravity.engine.pipeline import Pipeline; print('DarkGravity OK')"
```

Expected output: `DarkGravity OK`

8. Verify config files exist:
```bash
ls -la "$DARKGRAVITY_HOME/config/darkgravity.yaml" "$DARKGRAVITY_HOME/config/darkgravity_cheap.yaml"
```

Both config profiles should be present:
- `darkgravity.yaml` — standard config (default)
- `darkgravity_cheap.yaml` — budget-friendly config for lower-cost runs

9. Report to the user:
   - Engine location: `$DARKGRAVITY_HOME` (saved to `.agent/darkgravity.conf`)
   - Config profiles: `darkgravity.yaml` (standard), `darkgravity_cheap.yaml` (budget)
   - Web search: installed if optional step was run, otherwise `--web-search` will not work
   - Available workflows: `/darkgravity_research`, `/darkgravity_architect`, `/darkgravity_coder`, `/darkgravity_swarm`
   - No shell profile changes needed — `.agent/darkgravity.conf` persists the path automatically

## Troubleshooting

- If Python 3.11+ not found: install via `sudo apt install python3.11 python3.11-venv` or equivalent
- If clone fails (private repo): ensure SSH keys or token are configured for GitHub
- To reinstall: `rm -rf "$DARKGRAVITY_HOME"` and run this workflow again
- To change engine location: edit `.agent/darkgravity.conf` with the new path
- If `--web-search` fails later: re-run the optional pip install step above
