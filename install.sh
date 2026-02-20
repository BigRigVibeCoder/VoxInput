#!/bin/bash
# install.sh — VoxInput SOTA installer
# =====================================================
# Installs system deps, Python venv, Vosk model,
# registers .desktop launcher, and optionally sets up autostart.
#
# Usage:
#   ./install.sh              # full install
#   ./install.sh --no-model   # skip model download (if already present)
#   ./install.sh --autostart  # also configure autostart on login
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Flags ──────────────────────────────────────────────────────────────────
SKIP_MODEL=false
AUTOSTART=false
for arg in "$@"; do
    case $arg in
        --no-model)   SKIP_MODEL=true ;;
        --autostart)  AUTOSTART=true ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║          VoxInput Installer                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Sudo helper ────────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"
    else echo "ERROR: root or sudo required." && exit 1; fi
else SUDO=""; fi

# ── 0. Kill any running instances ──────────────────────────────────────────
echo "▶ Stopping any running VoxInput instances..."
pkill -f "VoxInput/run.py" 2>/dev/null || true

# ── 1. System dependencies ─────────────────────────────────────────────────
echo "▶ Installing system dependencies..."
$SUDO apt-get update -q
$SUDO apt-get install -y -q \
    python3-pip python3-venv \
    python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 \
    libportaudio2 portaudio19-dev \
    xdotool \
    ffmpeg unzip wget curl \
    libcairo2-dev gobject-introspection gir1.2-pango-1.0

# ── ydotool (Wayland-native backend, Phase 4) ──────────────────────────────
echo "▶ Installing ydotool (Wayland injection backend)..."
if ! command -v ydotool >/dev/null 2>&1; then
    $SUDO apt-get install -y -q ydotool 2>/dev/null || {
        echo "  ⚠ ydotool not in apt — attempting build from source..."
        if command -v cmake >/dev/null 2>&1; then
            tmp=$(mktemp -d)
            git clone --depth 1 https://github.com/ReimuNotMoe/ydotool.git "$tmp/ydotool"
            cmake -S "$tmp/ydotool" -B "$tmp/build" -DCMAKE_BUILD_TYPE=Release
            cmake --build "$tmp/build" -j"$(nproc)"
            $SUDO cmake --install "$tmp/build"
        else
            echo "  ⚠ cmake not found — ydotool skipped. xdotool will be used as fallback."
        fi
    }
else
    echo "  ✓ ydotool already installed"
fi

# ── Enable ydotoold daemon ─────────────────────────────────────────────────
if command -v ydotool >/dev/null 2>&1; then
    if ! pgrep -x ydotoold >/dev/null 2>&1; then
        echo "  Starting ydotoold daemon..."
        ydotoold &
        sleep 0.5
    else
        echo "  ✓ ydotoold already running"
    fi
fi

# ── 2. Python virtual environment ──────────────────────────────────────────
echo "▶ Setting up Python venv..."
if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Python dependencies installed"

# ── 3. Optional: faster-whisper ────────────────────────────────────────────
echo "▶ Installing faster-whisper (optional — Phase 2)..."
pip install faster-whisper -q 2>/dev/null && echo "  ✓ faster-whisper installed" || echo "  ⚠ faster-whisper skipped"

# ── 4. Optional: symspellpy ────────────────────────────────────────────────
echo "▶ Installing symspellpy (optional — Phase 3 spell correction)..."
pip install symspellpy -q 2>/dev/null && echo "  ✓ symspellpy installed" || echo "  ⚠ symspellpy skipped"

# ── 5. Download Vosk model ─────────────────────────────────────────────────
if [ "$SKIP_MODEL" = false ]; then
    MODEL_DIR="model"
    GIGASPEECH_DIR="$MODEL_DIR/gigaspeech"
    SMALL_DIR="$MODEL_DIR/default_model"

    mkdir -p "$MODEL_DIR"

    if [ -d "$GIGASPEECH_DIR" ]; then
        echo "▶ Vosk gigaspeech model already present — skipping download"
    elif [ -d "$SMALL_DIR" ]; then
        echo "▶ Vosk small model already present — skipping download"
    else
        echo "▶ Downloading Vosk small model (40MB)..."
        wget -q --show-progress \
            https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip \
            -O /tmp/vosk-model-small.zip
        unzip -q /tmp/vosk-model-small.zip -d "$MODEL_DIR"
        mv "$MODEL_DIR/vosk-model-small-en-us-0.15" "$SMALL_DIR"
        rm /tmp/vosk-model-small.zip
        echo "  ✓ Vosk model downloaded to $SMALL_DIR"
        echo "  ℹ For best accuracy, download the gigaspeech model:"
        echo "    https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip"
        echo "    Extract to: $GIGASPEECH_DIR"
    fi
else
    echo "▶ Skipping model download (--no-model)"
fi

# ── 6. Register .desktop launcher ──────────────────────────────────────────
echo "▶ Registering application launcher..."
DESKTOP_SRC="$SCRIPT_DIR/voxinput.desktop"
DESKTOP_DEST="$HOME/.local/share/applications/voxinput.desktop"

# Write a fully resolved .desktop file (absolute paths substituted)
mkdir -p "$HOME/.local/share/applications"
sed "s|/home/bdavidriggins/Documents/VoxInput|$SCRIPT_DIR|g" \
    "$DESKTOP_SRC" > "$DESKTOP_DEST"
chmod +x "$DESKTOP_DEST"

# Update desktop DB
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
echo "  ✓ Launcher registered: $DESKTOP_DEST"

# ── 7. Autostart (optional) ────────────────────────────────────────────────
if [ "$AUTOSTART" = true ]; then
    echo "▶ Setting up autostart on login..."
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"
    sed "s|X-GNOME-Autostart-enabled=false|X-GNOME-Autostart-enabled=true|" \
        "$DESKTOP_DEST" > "$AUTOSTART_DIR/voxinput.desktop"
    echo "  ✓ Autostart configured: $AUTOSTART_DIR/voxinput.desktop"
fi

# ── 8. Validate installation ───────────────────────────────────────────────
echo ""
echo "▶ Validating installation..."
PYTHONPATH="$SCRIPT_DIR" python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
issues = []
try: from src.config import SAMPLE_RATE, CHUNK_SIZE
except Exception as e: issues.append(f'config: {e}')
try: from src.settings import SettingsManager
except Exception as e: issues.append(f'settings: {e}')
try: from src.injection import TextInjector, apply_voice_punctuation
except Exception as e: issues.append(f'injection: {e}')
try: from src.hardware_profile import HardwareProfile
except Exception as e: issues.append(f'hardware_profile: {e}')
try: from src.spell_corrector import SpellCorrector
except Exception as e: issues.append(f'spell_corrector: {e}')
if issues:
    print('  ❌ Validation issues:')
    for i in issues: print(f'     - {i}')
    sys.exit(1)
else:
    print('  ✅ All core modules import cleanly')
" || echo "  ⚠ Validation had warnings (see above)"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ VoxInput installed successfully           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Launch: python3 run.py                      ║"
echo "║  Or:     find VoxInput in app launcher       ║"
echo "║  Hotkey: Super+V (configure in system settings)║"
echo "╚══════════════════════════════════════════════╝"
echo ""
