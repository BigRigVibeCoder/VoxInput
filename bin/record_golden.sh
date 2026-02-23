#!/bin/bash
# =============================================================================
# VoxInput — Golden Voice Capture Harness
# =============================================================================
# Records the user reading each test paragraph and saves them as permanent
# WER test fixtures. Run this ONCE to establish your accuracy baseline.
#
# Usage: ./bin/record_golden.sh [--paragraph A|B|C|D|all]
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GOLDEN_DIR="$PROJECT_DIR/tests/fixtures/golden"
OUTPUT_DIR="$GOLDEN_DIR/recordings"
GROUND_TRUTH="$GOLDEN_DIR/ground_truth.md"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

mkdir -p "$OUTPUT_DIR"

# ─────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────
PARAGRAPH="${1:-all}"
if [[ "$1" == "--paragraph" ]]; then
    PARAGRAPH="$2"
fi

# ─────────────────────────────────────────────
# Check dependencies
# ─────────────────────────────────────────────
for cmd in arecord aplay pactl ffmpeg; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}ERROR: '$cmd' not found. Install with:${RESET}"
        echo "  sudo apt install alsa-utils ffmpeg"
        exit 1
    fi
done

# ─────────────────────────────────────────────
# List available microphones
# ─────────────────────────────────────────────
print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD}  VoxInput — Golden Voice Capture Harness          ${RESET}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
    echo ""
}

list_mics() {
    echo -e "${BOLD}Available microphones:${RESET}"
    pactl list sources short | grep -v monitor | awk '{print NR". "$2}' || true
    echo ""
}

# ─────────────────────────────────────────────
# Countdown before recording
# ─────────────────────────────────────────────
countdown() {
    local label="$1"
    echo -e "\n${YELLOW}${BOLD}Recording: $label${RESET}"
    echo -e "Get ready to speak. Starting in:"
    for i in 3 2 1; do
        echo -e "  ${BOLD}$i...${RESET}"
        sleep 1
    done
    echo -e "${RED}${BOLD}🔴 RECORDING — SPEAK NOW${RESET}\n"
}

# ─────────────────────────────────────────────
# Record a single paragraph
# ─────────────────────────────────────────────
record_paragraph() {
    local label="$1"       # e.g. "A"
    local duration="$2"    # ignored — kept for backwards compat
    local output="$3"      # output .wav path
    local prompt="$4"      # text to display on screen

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}PARAGRAPH $label${RESET}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    # Display the paragraph text to read
    echo -e "${BOLD}READ THIS ALOUD:${RESET}"
    echo ""
    echo -e "$prompt"
    echo ""

    # ─── Auto-pause VoxInput so it doesn't intercept your speech ──
    local vox_pid=""
    if [ -f /tmp/voxinput.lock ]; then
        vox_pid=$(cat /tmp/voxinput.lock 2>/dev/null)
        if [ -n "$vox_pid" ] && kill -0 "$vox_pid" 2>/dev/null; then
            echo -e "${YELLOW}⏸  Pausing VoxInput (PID $vox_pid) during recording...${RESET}"
            kill -SIGUSR1 "$vox_pid" 2>/dev/null || true
            sleep 0.3
        else
            vox_pid=""
        fi
    fi

    echo -e "${YELLOW}Press ENTER when you are ready to start recording...${RESET}"
    read -r

    echo -e "\n${RED}${BOLD}🔴 RECORDING — SPEAK NOW${RESET}"
    echo -e "${YELLOW}   Press ENTER when you are done speaking.${RESET}\n"

    # Record indefinitely (no -d flag) — killed when user presses Enter
    arecord -f S16_LE \
            -r 16000 \
            -c 1 \
            --quiet \
            "$output" &
    RECORD_PID=$!

    # Show elapsed time while recording
    (
        elapsed=0
        while kill -0 "$RECORD_PID" 2>/dev/null; do
            printf "\r  🔴 Recording... %ds " "$elapsed"
            sleep 1
            (( elapsed++ )) || true
        done
    ) &
    TIMER_PID=$!

    # Wait for user to press Enter
    read -r

    # Stop recording
    kill "$RECORD_PID" 2>/dev/null
    wait "$RECORD_PID" 2>/dev/null || true
    kill "$TIMER_PID" 2>/dev/null
    wait "$TIMER_PID" 2>/dev/null || true
    echo ""

    # ─── Auto-resume VoxInput ──
    if [ -n "$vox_pid" ] && kill -0 "$vox_pid" 2>/dev/null; then
        echo -e "${GREEN}▶  Resuming VoxInput...${RESET}"
        kill -SIGUSR1 "$vox_pid" 2>/dev/null || true
    fi

    echo -e "\n${GREEN}✓ Recording saved: $output${RESET}"

    # ─── Quality Check ───────────────────────────────
    echo -e "\n${BOLD}Running quality check...${RESET}"
    # Get peak level via ffmpeg
    local level_info
    level_info=$(ffmpeg -i "$output" -filter:a "volumedetect" -f null /dev/null 2>&1 | grep "max_volume\|mean_volume")
    echo "  $level_info"

    local max_vol
    max_vol=$(echo "$level_info" | grep max_volume | awk '{print $5}')
    if (( $(echo "$max_vol > -3" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${RED}⚠  Audio may be clipped (max: ${max_vol}dB). Consider re-recording.${RESET}"
    elif (( $(echo "$max_vol < -20" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${YELLOW}⚠  Audio is quiet (max: ${max_vol}dB). Speak louder or move closer.${RESET}"
    else
        echo -e "  ${GREEN}✓  Audio levels look good (max: ${max_vol}dB)${RESET}"
    fi

    # ─── Playback ────────────────────────────────────
    echo ""
    echo -e "${YELLOW}Play back the recording? (y/N)${RESET}"
    read -r play_choice
    if [[ "$play_choice" =~ ^[Yy]$ ]]; then
        echo -e "Playing back..."
        aplay --quiet "$output"
    fi

    # ─── Accept or Re-record ─────────────────────────
    echo ""
    echo -e "${YELLOW}Accept this recording? (Y/n)${RESET}"
    read -r accept
    if [[ "$accept" =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}Re-recording Paragraph $label...${RESET}"
        record_paragraph "$label" "$duration" "$output" "$prompt"
    else
        echo -e "${GREEN}✓ Paragraph $label accepted.${RESET}"
    fi
}

# ─────────────────────────────────────────────
# Convert WAV → raw PCM for direct engine use
# ─────────────────────────────────────────────
convert_to_raw() {
    local wav="$1"
    local raw="${wav%.wav}.raw"
    ffmpeg -y -i "$wav" -f s16le -ar 16000 -ac 1 "$raw" -loglevel quiet
    echo -e "  ${GREEN}✓  Converted: $(basename "$raw")${RESET}"
}

# ─────────────────────────────────────────────
# Paragraph text definitions
# ─────────────────────────────────────────────
PARA_A="The weather forecast said there would be two inches of rain by four o'clock.
Their car broke down near the old library, so they had to walk through the park.
She said she could hear the music from here, but I wasn't so sure.
We need to buy flour, sugar, and eight eggs for the recipe.
The president met with senators from Colorado and New Mexico on Tuesday.
Please write your name, date of birth, and a brief description of the problem.
He ran quickly across the bridge, jumped over the fence, and disappeared into the night."

PARA_B="Call me at five five five, one two three four between nine and five on weekdays.
The temperature dropped to thirty two degrees on the fifteenth of January.
Doctor Johnson prescribed four hundred milligrams twice a day for ten days.
Amazon, Google, and Microsoft reported record earnings in the third quarter.
The flight departs from terminal three at seven forty five in the morning."

PARA_C="I want to go to the store too if you are going there.
The knight knew the night would be long as he rode through the forest.
They're going to their house over there on the hill by the lake.
The principal principle is that every student deserves a fair chance to succeed.
She wore a blue dress to the gym where she blew out her knee doing squats."

PARA_D="This is a continuous sentence designed to test how well the recognizer handles long uninterrupted speech without any natural pauses or sentence breaks because sometimes people talk in long run-on sentences when they are excited or in the middle of explaining something complex and the system needs to handle that gracefully without losing words or injecting garbage."

PARA_E="Dear mister Thompson comma I am writing to confirm your appointment on March twenty first at three forty five in the afternoon period new line The total cost is two hundred and fifteen dollars and sixty three cents semicolon please bring a valid photo ID period new line Can you meet me at twelve thirty question mark I need to discuss items one comma two comma and three before the deadline period new line Warning exclamation mark The system detected forty seven errors in section nine dash alpha colon please review immediately period new line He said quote I'll be there by five o'clock quote dash but honestly comma I wouldn't count on it period"

PARA_F="The Docker container ran on the Kubernetes cluster period We checked the Grafana dashboard and the Jira backlog during our sprint standup period The Terraform configuration managed the Tailscale network in Colorado and Virginia period We used PyTorch and TensorFlow for training comma and the nginx reverse proxy handled the API gateway period The Ansible playbook deployed to fifteen nodes comma and Slack and Discord were used for team coordination period"

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
print_header
list_mics

echo -e "${BOLD}This session will record your voice reading each test paragraph.${RESET}"
echo -e "Your recordings become permanent test fixtures for WER accuracy testing."
echo -e "You only need to do this ${BOLD}once${RESET}.\n"
echo -e "${YELLOW}Press ENTER to begin, or Ctrl+C to cancel.${RESET}"
read -r

echo ""
echo -e "${BOLD}Which paragraphs? [all / A / B / C / D / E / F]:${RESET}"
read -r PARAGRAPH
PARAGRAPH="${PARAGRAPH:-all}"

run_paragraph() {
    local p="$1"
    case "$p" in
        A|a) record_paragraph "A" 55 "$OUTPUT_DIR/paragraph_a.wav" "$PARA_A" ;;
        B|b) record_paragraph "B" 45 "$OUTPUT_DIR/paragraph_b.wav" "$PARA_B" ;;
        C|c) record_paragraph "C" 50 "$OUTPUT_DIR/paragraph_c.wav" "$PARA_C" ;;
        D|d) record_paragraph "D" 60 "$OUTPUT_DIR/paragraph_d.wav" "$PARA_D" ;;
        E|e) record_paragraph "E" 65 "$OUTPUT_DIR/paragraph_e.wav" "$PARA_E" ;;
        F|f) record_paragraph "F" 50 "$OUTPUT_DIR/paragraph_f.wav" "$PARA_F" ;;
        *) echo "Unknown paragraph: $p" ;;
    esac
}

case "${PARAGRAPH^^}" in
    ALL)
        for p in A B C D E F; do run_paragraph "$p"; done
        ;;
    *)
        run_paragraph "$PARAGRAPH"
        ;;
esac

# ─────────────────────────────────────────────
# Convert all recorded WAVs to raw PCM
# ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}Converting recordings to raw PCM (for direct engine testing)...${RESET}"
for wav in "$OUTPUT_DIR"/*.wav; do
    [ -f "$wav" ] && convert_to_raw "$wav"
done

# ─────────────────────────────────────────────
# Generate session report
# ─────────────────────────────────────────────
REPORT="$OUTPUT_DIR/session_report.txt"
{
    echo "VoxInput Golden Recording Session"
    echo "=================================="
    echo "Date: $(date)"
    echo "Host: $(hostname)"
    echo ""
    echo "Recordings:"
    for wav in "$OUTPUT_DIR"/*.wav; do
        if [ -f "$wav" ]; then
            size=$(du -h "$wav" | cut -f1)
            dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$wav" 2>/dev/null | xargs printf "%.1fs" || echo "?")
            echo "  $(basename "$wav")  $size  $dur"
        fi
    done
    echo ""
    echo "Run WER tests with:"
    echo "  pytest tests/golden/ -v -s -m golden"
} > "$REPORT"

cat "$REPORT"

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  Recording session complete!                       ${RESET}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "Run WER accuracy tests:"
echo -e "  ${CYAN}pytest tests/golden/ -v -s -m golden${RESET}"
echo ""
