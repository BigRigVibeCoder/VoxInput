#!/bin/bash
# =============================================================================
# VoxInput — Add Compound Correction (Zero Restart)
# =============================================================================
# Adds a compound correction to the database and hot-reloads VoxInput.
# No restart required!
#
# Usage:
#   ./bin/add_correction.sh "misheard phrase" "CorrectWord"
#
# Examples:
#   ./bin/add_correction.sh "have my" "HiveMind"
#   ./bin/add_correction.sh "pie torch" "PyTorch"
#   ./bin/add_correction.sh "cooper eighties" "kubernetes"
#
# The correction takes effect immediately — no restart needed.
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_DIR/data/custom_words.db"
LOCK_FILE="/tmp/voxinput.lock"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ─── Argument check ─────────────────────────────────
if [ $# -lt 2 ]; then
    echo -e "${BOLD}Usage:${RESET} $0 \"misheard phrase\" \"CorrectWord\""
    echo ""
    echo -e "${BOLD}Examples:${RESET}"
    echo "  $0 \"have my\" \"HiveMind\""
    echo "  $0 \"pie torch\" \"PyTorch\""
    echo "  $0 \"cooper eighties\" \"kubernetes\""
    echo ""
    echo -e "${CYAN}List current corrections:${RESET}"
    echo "  $0 --list"
    exit 1
fi

# ─── List mode ───────────────────────────────────────
if [ "$1" == "--list" ]; then
    echo -e "${BOLD}Current compound corrections:${RESET}"
    cd "$PROJECT_DIR" && source venv/bin/activate 2>/dev/null
    python3 -c "
from src.word_db import WordDatabase
db = WordDatabase('$DB_PATH')
compounds = db.get_all_compounds()
for misheard, correct in sorted(compounds):
    print(f'  \"{misheard}\" → \"{correct}\"')
print(f'\nTotal: {len(compounds)}')
db.close()
" 2>/dev/null
    exit 0
fi

MISHEARD="$1"
CORRECT="$2"

# ─── Add to database ────────────────────────────────
echo -e "${BOLD}Adding compound correction...${RESET}"
cd "$PROJECT_DIR" && source venv/bin/activate 2>/dev/null

RESULT=$(python3 -c "
from src.word_db import WordDatabase
db = WordDatabase('$DB_PATH')
added = db.add_compound_correction('$MISHEARD', '$CORRECT')
if added:
    print('ADDED')
else:
    print('EXISTS')
print(len(db.get_compound_corrections()))
db.close()
" 2>/dev/null)

STATUS=$(echo "$RESULT" | head -1)
COUNT=$(echo "$RESULT" | tail -1)

if [ "$STATUS" == "ADDED" ]; then
    echo -e "  ${GREEN}✓${RESET} \"${MISHEARD}\" → \"${CORRECT}\" added to database"
else
    echo -e "  ${YELLOW}⚠${RESET} \"${MISHEARD}\" → \"${CORRECT}\" already exists"
fi
echo -e "  ${CYAN}Total compound corrections: ${COUNT}${RESET}"

# ─── Signal VoxInput to hot-reload ──────────────────
if [ -f "$LOCK_FILE" ]; then
    VOX_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$VOX_PID" ] && kill -0 "$VOX_PID" 2>/dev/null; then
        kill -USR2 "$VOX_PID"
        echo -e "  ${GREEN}✓${RESET} VoxInput (PID $VOX_PID) hot-reloaded — correction active now!"
    else
        echo -e "  ${YELLOW}⚠${RESET} VoxInput not running — correction will load on next start"
    fi
else
    echo -e "  ${YELLOW}⚠${RESET} VoxInput not running — correction will load on next start"
fi

echo ""
