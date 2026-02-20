#!/usr/bin/env bash
# src/c_ext/build.sh — compile VoxInput C extensions
# Run from repo root or src/c_ext/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "▶ Building VoxInput C extensions..."

if ! command -v gcc &>/dev/null; then
    echo "  ⚠ gcc not found — C extensions skipped (falling back to numpy RMS)"
    exit 0
fi

gcc -O3 -march=native -shared -fPIC \
    -o librms.so rms.c -lm \
    2>&1 && echo "  ✓ librms.so built" || {
    echo "  ⚠ librms.so build failed — falling back to numpy RMS"
    exit 0
}

# Verify it loads
python3 -c "
import ctypes, pathlib
lib = ctypes.CDLL(str(pathlib.Path('$SCRIPT_DIR') / 'librms.so'))
print('  ✓ librms.so loads cleanly')
"
