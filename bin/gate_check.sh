#!/usr/bin/env bash
# bin/gate_check.sh — VoxInput full gate check suite
# ======================================================
# Runs all gates in sequence. Each gate must pass before the next runs.
# Gate 0: Unit/integration tests (pytest, no hardware required)
# Gate 1: Vosk WER accuracy test (requires model + recordings)
#
# Usage:
#   ./bin/gate_check.sh              # all gates
#   ./bin/gate_check.sh 0            # gate 0 only (fast, no model needed)
#   ./bin/gate_check.sh wer          # WER gate only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

# Activate venv if present
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
fi

GATE="${1:-all}"
PASS_COUNT=0
FAIL_COUNT=0

_header() { echo ""; echo "══════════════════════════════════════════════"; echo "  $1"; echo "══════════════════════════════════════════════"; }
_pass()   { echo "  ✅ $1"; ((PASS_COUNT++)) || true; }
_fail()   { echo "  ❌ $1"; ((FAIL_COUNT++)) || true; }

# ─── GATE 0: Unit + Integration + E2E (mocked, fast) ───────────────────────

gate_0() {
    _header "GATE 0 — Unit / Integration Tests"
    local result
    if PYTHONPATH=. pytest tests/ --ignore=tests/golden -q --tb=short 2>&1; then
        _pass "All pytest tests passed"
    else
        _fail "pytest tests failed — fix before proceeding to Gate 1"
        return 1
    fi
}

# ─── GATE 1: Golden WER Accuracy (real Vosk model) ──────────────────────────

gate_wer() {
    _header "GATE 1 — Golden WER Accuracy (Vosk Gigaspeech)"

    local recordings_dir="tests/fixtures/golden/recordings"
    if ! ls "$recordings_dir"/paragraph_a.raw &>/dev/null; then
        echo "  ⚠️  No golden recordings found — skipping WER gate"
        echo "     Run: ./bin/record_golden.sh"
        return 0
    fi

    if python3 bin/run_wer.py; then
        _pass "WER gate passed"
    else
        _fail "WER gate failed — see output above"
        return 1
    fi
}

# ─── Summary ───────────────────────────────────────────────────────────────

summary() {
    echo ""
    echo "══════════════════════════════════════════════"
    echo "  GATE SUMMARY: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
    if [[ $FAIL_COUNT -eq 0 ]]; then
        echo "  ✅ ALL GATES PASS — branch is releasable"
    else
        echo "  ❌ GATE FAILURES — do NOT merge"
    fi
    echo "══════════════════════════════════════════════"
    echo ""
    [[ $FAIL_COUNT -eq 0 ]]
}

# ─── Run ───────────────────────────────────────────────────────────────────

case "$GATE" in
    0)   gate_0; summary ;;
    wer) gate_wer; summary ;;
    all) gate_0 && gate_wer; summary ;;
    *)   echo "Usage: $0 [0|wer|all]"; exit 1 ;;
esac
