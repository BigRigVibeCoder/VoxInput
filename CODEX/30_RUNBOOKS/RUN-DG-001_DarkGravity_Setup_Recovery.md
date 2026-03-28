---
id: RUN-DG-001
title: "DarkGravity Setup & Recovery Guide"
type: how-to
status: APPROVED
owner: architect
version: "1.0.0"
created: "2026-03-10"
updated: "2026-03-18"
tags: [darkgravity, setup, recovery, workflow]
agents: [coder, researcher, architect]
related: []
---

> **BLUF:** Install, configure, and recover the DarkGravity multi-agent swarm engine. Covers fresh install, auto-discovery via `bin/resolve_darkgravity.sh`, API key setup, troubleshooting, and nuclear recovery.

# DarkGravity Setup & Recovery Guide

## 1. What Is DarkGravity?

A multi-agent swarm engine providing 4 AI agents (Researcher → Architect → Coder → Tester), each reviewed by a 4-persona adversarial swarm. It runs as a CLI tool invoked from agent workflows.

**Repo**: https://github.com/BigRigVibeCoder/darkgravity

## 2. How This Template Finds DarkGravity

The template uses a **two-piece discovery mechanism** so you never need to set env vars manually:

| File | Purpose |
|:--|:--|
| `bin/resolve_darkgravity.sh` | Sourced by every workflow; finds the engine in priority order |
| `.agent/darkgravity.conf` | Machine-local, gitignored; stores `DARKGRAVITY_HOME=/path/to/clone` |

**Priority order** (first match wins):
1. `.agent/darkgravity.conf` — written by `/darkgravity_setup`, most reliable
2. `$DARKGRAVITY_HOME` env var — power-user override
3. Sibling directory search — `../darkgravity`, `~/Documents/darkgravity`, etc.
4. `~/.darkgravity-engine/` — legacy fallback

To **reset** the path: edit `.agent/darkgravity.conf` with the correct path.
To **override** for one session: `export DARKGRAVITY_HOME=/new/path` before running.

## 3. Requirements

- **Python 3.11+** (`python3 --version`)
- **Git** (`git --version`)
- **Google AI Studio API key** (free): https://aistudio.google.com/apikey
- ~500MB disk for venv + dependencies

## 4. Fresh Install

The easiest way is to run `/darkgravity_setup` — it auto-discovers an existing clone and saves the path. For a manual install:

```bash
# 1. Clone next to your project (sibling dir is auto-detected)
DARKGRAVITY_HOME="$(dirname $(git rev-parse --show-toplevel))/darkgravity"
git clone https://github.com/BigRigVibeCoder/darkgravity.git "$DARKGRAVITY_HOME"

# 2. Create venv and install
python3 -m venv "$DARKGRAVITY_HOME/.venv"
"$DARKGRAVITY_HOME/.venv/bin/pip" install --upgrade pip
"$DARKGRAVITY_HOME/.venv/bin/pip" install -e "$DARKGRAVITY_HOME"

# 3. Configure API keys
cat > "$DARKGRAVITY_HOME/.env" << 'EOF'
DG_GOOGLE_AI_API_KEY=YOUR_KEY_HERE
# DG_OPENROUTER_API_KEY=sk-or-v1-...  # optional paid fallback
EOF

# 4. Save path to template config (no shell profile changes needed)
echo "DARKGRAVITY_HOME=$DARKGRAVITY_HOME" > .agent/darkgravity.conf

# 5. Verify
"$DARKGRAVITY_HOME/.venv/bin/python3" -c \
  "from darkgravity.engine.pipeline import Pipeline; print('OK')"
```

## 5. Shell Configuration (Optional)

No shell profile changes are required. The `.agent/darkgravity.conf` file persists the path.

If you prefer a global override, add to `~/.bashrc` (or `~/.zshrc`):

```bash
export DARKGRAVITY_HOME=/path/to/your/darkgravity
```

The env var takes priority over `.agent/darkgravity.conf`.

## 6. Quick Verify

```bash
# Resolver finds the engine?
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
source "$PROJECT_ROOT/bin/resolve_darkgravity.sh" && echo "FOUND: $DARKGRAVITY_HOME"

# Python import works?
"$DARKGRAVITY_HOME/.venv/bin/python3" -c \
  "from darkgravity.engine.pipeline import Pipeline; print('OK')"

# CLI works?
bash "$DARKGRAVITY_HOME/bin/run_pipeline.sh" \
  --request "Hello world test" \
  --project /tmp --stages researcher --json
```

## 7. Troubleshooting

### ModuleNotFoundError
```bash
cd "$DARKGRAVITY_HOME" && .venv/bin/pip install -e .
```

### API Key Errors
```bash
cat "$DARKGRAVITY_HOME/.env"       # check keys are set
# Test Google AI key directly:
curl "https://generativelanguage.googleapis.com/v1/models?key=YOUR_KEY"
```

### venv Corrupted / Python Version Mismatch
```bash
rm -rf "$DARKGRAVITY_HOME/.venv"
python3 -m venv "$DARKGRAVITY_HOME/.venv"
"$DARKGRAVITY_HOME/.venv/bin/pip" install --upgrade pip
"$DARKGRAVITY_HOME/.venv/bin/pip" install -e "$DARKGRAVITY_HOME"
```

### Stale Code (need latest from GitHub)
```bash
cd "$DARKGRAVITY_HOME"
git pull origin main
.venv/bin/pip install -e .
```

## 8. Nuclear Recovery (Full Wipe & Reinstall)

If everything is broken beyond repair:

```bash
# Backup API keys first
cp "$DARKGRAVITY_HOME/.env" /tmp/darkgravity_env_backup

# Wipe
rm -rf "$DARKGRAVITY_HOME"

# Reinstall (steps from Section 3)
git clone https://github.com/BigRigVibeCoder/darkgravity.git "$DARKGRAVITY_HOME"
python3 -m venv "$DARKGRAVITY_HOME/.venv"
"$DARKGRAVITY_HOME/.venv/bin/pip" install --upgrade pip
"$DARKGRAVITY_HOME/.venv/bin/pip" install -e "$DARKGRAVITY_HOME"

# Restore keys
cp /tmp/darkgravity_env_backup "$DARKGRAVITY_HOME/.env"
```

## 9. Available Slash Commands

| Command | What It Does |
|:--|:--|
| `/darkgravity_setup` | Automated version of this guide |
| `/darkgravity_research` | Research swarm on a topic |
| `/darkgravity_architect` | Generate architecture / task backlog |
| `/darkgravity_coder` | Code generation + test fix loop |
| `/darkgravity_swarm` | Full 4-stage pipeline |

## 10. Cost & Performance

- **Free tier** (Google AI Studio): $0.00 per run
- **Paid fallback** (OpenRouter): ~$0.01-$0.10 per run
- **Research stage**: ~30-60 seconds
- **Full pipeline**: ~5-15 minutes
- **Each stage**: 4-persona adversarial review (16 LLM calls per stage)
