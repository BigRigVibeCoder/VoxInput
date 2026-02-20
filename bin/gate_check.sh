#!/usr/bin/env bash
# bin/gate_check.sh — VoxInput full gate check suite
# ======================================================
# Gate 0: Unit/integration tests (pytest, mocked, ~3s)
# Gate 1: Vosk WER accuracy (real model + golden recordings, ~90s)
# Gate 2: E2E on Xvfb (xterm + screenshots + HTML report, ~3min)
# Gate 3: Logging compliance (SQLite WAL, TRACE level, auto-trim, excepthook)
#
# Usage:
#   ./bin/gate_check.sh              # all gates
#   ./bin/gate_check.sh 0            # Gate 0 only (fast)
#   ./bin/gate_check.sh wer          # Gate 1 WER only
#   ./bin/gate_check.sh e2e          # Gate 2 E2E only
#   ./bin/gate_check.sh 3            # Gate 3 logging compliance only

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

# ─── GATE 0: Unit + Integration (mocked, fast) ──────────────────────────────

gate_0() {
    _header "GATE 0 — Unit / Integration Tests"
    if PYTHONPATH="$ROOT" pytest tests/ --ignore=tests/golden --ignore=tests/e2e -q --tb=short 2>&1; then
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

    if PYTHONPATH="$ROOT" python3 bin/run_wer.py; then
        _pass "WER gate passed"
    else
        _fail "WER gate failed — see output above"
        return 1
    fi
}

# ─── GATE 2: E2E on Xvfb (xterm + screenshots + report) ─────────────────────

gate_e2e() {
    _header "GATE 2 — E2E Integration Test (Xvfb + xterm + screenshots)"

    if ! command -v Xvfb &>/dev/null; then
        echo "  ⚠️  Xvfb not found — install with: sudo apt install xvfb"
        return 1
    fi

    local recordings_dir="tests/fixtures/golden/recordings"
    if ! ls "$recordings_dir"/paragraph_a.wav &>/dev/null; then
        echo "  ⚠️  No golden WAV recordings found — skipping E2E gate"
        return 0
    fi

    mkdir -p reports

    # Export PYTHONPATH before xvfb-run so it's inherited by the subprocess
    export PYTHONPATH="$ROOT"

    if xvfb-run -a --server-args="-screen 0 1280x900x24" \
        pytest tests/e2e/test_golden_e2e.py \
            -v -s --tb=short --no-header 2>&1; then
        _pass "E2E gate passed — report: reports/e2e_report.html"
    else
        _fail "E2E gate failed — see reports/e2e_report.html for details"
        return 1
    fi
}

# ─── GATE 3: Logging Compliance (HM-IPV-005/003/018) ────────────────────────

gate_3() {
    _header "GATE 3 — Logging Compliance (TRACE level, SQLite WAL, auto-trim)"

    # Run logging unit tests
    if PYTHONPATH="$ROOT" pytest tests/unit/test_logger.py -v --tb=short --no-header -q 2>&1; then
        _pass "Logging unit tests passed (20 tests)"
    else
        _fail "Logging unit tests failed"
        return 1
    fi

    # Smoke: DB created + WAL active + TRACE rows land in DB
    local smoke_db="/tmp/voxinput_gate3_smoke_$$.db"
    local smoke_out
    smoke_out=$(PYTHONPATH="$ROOT" LOG_LEVEL=TRACE LOG_CONSOLE=false LOG_DB_PATH="$smoke_db" \
        python3 -c "
import sys, time, sqlite3, os
sys.path.insert(0,'.')
from src.logger import init_logging, get_logger, TRACE
init_logging('gate3')
log = get_logger('smoke')
log.info('gate3_info')
log.trace('gate3_trace')
time.sleep(0.35)
c = sqlite3.connect(os.environ['LOG_DB_PATH'])
mode = c.execute('PRAGMA journal_mode').fetchone()[0]
count = c.execute('SELECT COUNT(*) FROM system_logs').fetchone()[0]
c.close()
assert mode == 'wal', f'WAL not active: {mode}'
assert count >= 1, f'No rows written: {count}'
print(f'SMOKE_OK WAL={mode} rows={count}')
" 2>&1)
    rm -f "$smoke_db" "${smoke_db}-wal" "${smoke_db}-shm" 2>/dev/null || true

    if echo "$smoke_out" | grep -q "SMOKE_OK"; then
        _pass "SQLite smoke test: $(echo "$smoke_out" | grep SMOKE_OK)"
    else
        _fail "SQLite smoke test failed: $smoke_out"
        return 1
    fi
}

# ─── GATE 4: Performance Benchmark (P8) ─────────────────────────────────────

gate_4() {
    _header "GATE 4 — Performance Benchmark (C RMS, deque, Whisper ring buffer)"

    # Ensure C extension is compiled
    if [[ -f "$ROOT/src/c_ext/build.sh" ]]; then
        bash "$ROOT/src/c_ext/build.sh" 2>&1 | sed 's/^/  /'
    fi

    # Run performance unit tests
    if PYTHONPATH="$ROOT" pytest tests/unit/test_perf.py \
        -v --tb=short --no-header -q \
        -k "not test_silence_settings_cached" 2>&1; then
        _pass "Performance benchmark tests passed"
    else
        _fail "Performance benchmark tests failed"
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
    e2e) gate_e2e; summary ;;
    3)   gate_3; summary ;;
    4)   gate_4; summary ;;
    all) gate_0 && gate_wer && gate_e2e && gate_3 && gate_4; summary ;;
    *)   echo "Usage: $0 [0|wer|e2e|3|4|all]"; exit 1 ;;
esac
