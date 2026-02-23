---
description: Reset the VoxInput environment — kill all processes, free memory, prepare for clean testing
---

# Reset VoxInput Environment

Use this workflow before running tests or when processes are hung/eating memory.

## 1. Kill VoxInput Application
// turbo
```bash
pkill -f "VoxInput/run.py" 2>/dev/null; sleep 1
echo "VoxInput stopped"
```

## 2. Kill ALL Stale Python Processes (test scripts, model loaders, etc.)
// turbo
```bash
# Kill any python process related to VoxInput (except this shell)
pkill -f "python.*VoxInput" 2>/dev/null
pkill -f "python.*-c.*import" 2>/dev/null
pkill -f "python.*pytest" 2>/dev/null
sleep 2
echo "Stale processes killed"
```

## 3. Verify Clean State
// turbo
```bash
echo "=== Remaining Python ===" && pgrep -af python 2>/dev/null || echo "None"
echo ""
echo "=== Memory ===" && free -h | head -3
echo ""
echo "=== Swap ===" && swapon --show 2>/dev/null
```

Expected: 0 python processes, 15+ GB available memory, minimal swap usage.

## 4. Clear Stale Lock Files
// turbo
```bash
PROJ_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
rm -f /tmp/voxinput.lock 2>/dev/null
rm -f "$PROJ_DIR"/*.log 2>/dev/null
echo "Lock files and logs cleared"
```

## 5. Verify Audio Subsystem
// turbo
```bash
echo "=== PulseAudio ===" && pactl info 2>/dev/null | grep "Default Source" || echo "PulseAudio not running"
echo "=== H390 Headset ===" && pactl list sources short 2>/dev/null | grep -i "headset\|VoxInput" || echo "No headset found"
```

## 6. Ready — Choose Next Action

At this point the environment is clean. Choose one:

### Run Unit Tests (fast, no model load)
```bash
cd "$(git rev-parse --show-toplevel)" && source venv/bin/activate && python -m pytest tests/unit -q --tb=short
```

### Run Unit Tests with Coverage
```bash
cd "$(git rev-parse --show-toplevel)" && source venv/bin/activate && python -m pytest tests/unit -q --tb=short --cov=src --cov-report=term-missing
```

### Restart VoxInput (after testing)
```bash
PROJ_DIR="$(git rev-parse --show-toplevel)"
source "$PROJ_DIR/venv/bin/activate" && nohup python "$PROJ_DIR/run.py" > "$PROJ_DIR/startup_trace.log" 2>&1 & disown
sleep 3 && pgrep -af "VoxInput/run.py"
```

### WER Test (requires ~4GB free RAM for gigaspeech model)
**IMPORTANT**: Do NOT run WER tests while VoxInput is running — the gigaspeech model needs ~2.3GB RAM and loading two copies will hang the system.
```bash
cd "$(git rev-parse --show-toplevel)" && source venv/bin/activate
# Stop VoxInput FIRST, then:
timeout 120 python -u tools/wer_paragraph.py
# Restart VoxInput AFTER
```
