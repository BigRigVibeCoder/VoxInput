"""
tests/golden/wer_report.py
===========================
Utilities for normalizing text and generating human-readable WER diff reports.

Can be run standalone:
  python3 tests/golden/wer_report.py --check-audio
  python3 tests/golden/wer_report.py --report tests/fixtures/golden/recordings/
"""

import os
import re
import sys
import argparse
import subprocess

# ─────────────────────────────────────────────────────────────
# Text Normalization
# ─────────────────────────────────────────────────────────────

def normalize_text(text: str, strip_punctuation: bool = True) -> str:
    """
    Normalize ASR output and ground truth to a fair comparison baseline.

    Steps:
      1. Lowercase
      2. Expand common contractions (won't → will not, etc.)
      3. Optionally strip punctuation (for Vosk vs Whisper parity)
      4. Collapse whitespace

    Args:
        text: Raw transcript or ground truth string
        strip_punctuation: If True, remove punctuation before comparison.
                           Use True for Vosk (no punctuation).
                           Use False when testing Whisper punctuation accuracy.
    """
    text = text.lower().strip()

    # Expand contractions for fairer comparison
    contractions = {
        "won't":    "will not",
        "can't":    "cannot",
        "i'm":      "i am",
        "i've":     "i have",
        "i'd":      "i would",
        "i'll":     "i will",
        "they're":  "they are",
        "they've":  "they have",
        "we're":    "we are",
        "we've":    "we have",
        "didn't":   "did not",
        "doesn't":  "does not",
        "don't":    "do not",
        "wasn't":   "was not",
        "weren't":  "were not",
        "isn't":    "is not",
        "aren't":   "are not",
        "hadn't":   "had not",
        "hasn't":   "has not",
        "haven't":  "have not",
        "wouldn't": "would not",
        "couldn't": "could not",
        "shouldn't": "should not",
        "that's":   "that is",
        "it's":     "it is",
        "what's":   "what is",
        "who's":    "who is",
        "there's":  "there is",
        "here's":   "here is",
        "o'clock":  "oclock",
    }
    for contraction, expansion in contractions.items():
        text = text.replace(contraction, expansion)

    if strip_punctuation:
        text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace
    text = " ".join(text.split())
    return text


# ─────────────────────────────────────────────────────────────
# Word-Level Diff
# ─────────────────────────────────────────────────────────────

def word_diff(reference: str, hypothesis: str) -> list[tuple[str, str]]:
    """
    Produce a word-level diff between reference and hypothesis.
    Returns list of (status, word) tuples where status is:
      'match'  — word is correct
      'sub'    — word was substituted
      'del'    — word was deleted (in ref, missing in hyp)
      'ins'    — word was inserted (in hyp, not in ref)
    Uses a simple DP alignment (edit distance traceback).
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    n, m = len(ref_words), len(hyp_words)

    # DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])

    # Traceback
    alignment = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_words[i-1] == hyp_words[j-1]:
            alignment.append(("match", ref_words[i-1]))
            i -= 1; j -= 1
        elif j > 0 and (i == 0 or dp[i][j-1] <= dp[i-1][j] and dp[i][j-1] <= dp[i-1][j-1]):
            alignment.append(("ins", hyp_words[j-1]))
            j -= 1
        elif i > 0 and (j == 0 or dp[i-1][j] <= dp[i][j-1] and dp[i-1][j] <= dp[i-1][j-1]):
            alignment.append(("del", ref_words[i-1]))
            i -= 1
        else:
            alignment.append(("sub", f"{ref_words[i-1]}→{hyp_words[j-1]}"))
            i -= 1; j -= 1

    return list(reversed(alignment))


# ─────────────────────────────────────────────────────────────
# Report Builder
# ─────────────────────────────────────────────────────────────

def build_diff_report(
    reference: str,
    hypothesis: str,
    wer_score: float,
    cer_score: float | None,
    threshold: float,
    engine_label: str,
    paragraph_label: str,
) -> dict:
    """Build a structured WER report dict."""
    passed = wer_score <= threshold
    alignment = word_diff(reference, hypothesis)

    errors = {
        "substitutions": sum(1 for s, _ in alignment if s == "sub"),
        "deletions":     sum(1 for s, _ in alignment if s == "del"),
        "insertions":    sum(1 for s, _ in alignment if s == "ins"),
        "matches":       sum(1 for s, _ in alignment if s == "match"),
    }

    return {
        "engine": engine_label,
        "paragraph": paragraph_label,
        "reference": reference,
        "hypothesis": hypothesis,
        "wer": wer_score,
        "cer": cer_score,
        "threshold": threshold,
        "passed": passed,
        "errors": errors,
        "alignment": alignment,
    }


def print_wer_report(report: dict) -> None:
    """Print a formatted WER report to stdout."""
    GREEN = "\033[0;32m"
    RED   = "\033[0;31m"
    YELLOW = "\033[1;33m"
    CYAN  = "\033[0;36m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"
    RESET = "\033[0m"

    status = f"{GREEN}✅ PASS{RESET}" if report["passed"] else f"{RED}❌ FAIL{RESET}"
    wer_color = GREEN if report["passed"] else RED

    print(f"\n{CYAN}{'─'*62}{RESET}")
    print(f"{BOLD}  {report['engine']} — {report['paragraph']}{RESET}")
    print(f"{CYAN}{'─'*62}{RESET}")
    print(f"  WER:       {wer_color}{report['wer']:.1%}{RESET}  (threshold: {report['threshold']:.0%})  {status}")
    if report["cer"] is not None:
        print(f"  CER:       {report['cer']:.1%}")
    e = report["errors"]
    print(f"  Errors:    {RED}{e['substitutions']} sub{RESET}  "
          f"{YELLOW}{e['deletions']} del{RESET}  "
          f"{CYAN}{e['insertions']} ins{RESET}  "
          f"{GREEN}{e['matches']} match{RESET}")

    # Word-level diff (show only errors, max 10)
    print(f"\n  {BOLD}Error Alignment{RESET} (errors highlighted):")
    error_count = 0
    for status_tag, word in report["alignment"]:
        if status_tag == "match":
            continue
        if error_count >= 10:
            print(f"  {DIM}... (more errors omitted){RESET}")
            break
        if status_tag == "sub":
            ref_w, hyp_w = word.split("→")
            print(f"    {RED}SUB{RESET}  expected: '{ref_w}'  got: '{hyp_w}'")
        elif status_tag == "del":
            print(f"    {YELLOW}DEL{RESET}  missing:  '{word}'")
        elif status_tag == "ins":
            print(f"    {CYAN}INS{RESET}  extra:    '{word}'")
        error_count += 1

    if error_count == 0:
        print(f"    {GREEN}(no errors){RESET}")

    print(f"{CYAN}{'─'*62}{RESET}\n")


# ─────────────────────────────────────────────────────────────
# Standalone CLI — Audio Quality Check
# ─────────────────────────────────────────────────────────────

def check_audio_quality(recordings_dir: str) -> None:
    """Verify recorded WAV files meet quality requirements."""
    print(f"\nChecking audio quality in: {recordings_dir}\n")
    found = False
    for fname in sorted(os.listdir(recordings_dir)):
        if not fname.endswith(".wav"):
            continue
        found = True
        path = os.path.join(recordings_dir, fname)

        try:
            # Check sample rate and channels
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", path],
                capture_output=True, text=True, check=True
            )
            import json
            info = json.loads(probe.stdout)
            stream = info["streams"][0] if info.get("streams") else {}
            sample_rate = stream.get("sample_rate", "?")
            channels = stream.get("channels", "?")
            duration = float(stream.get("duration", 0))

            # Check volume
            vol = subprocess.run(
                ["ffmpeg", "-i", path, "-filter:a", "volumedetect",
                 "-f", "null", "/dev/null"],
                capture_output=True, text=True
            )
            max_vol = "?"
            mean_vol = "?"
            for line in vol.stderr.split("\n"):
                if "max_volume" in line:
                    max_vol = line.split(":")[-1].strip()
                if "mean_volume" in line:
                    mean_vol = line.split(":")[-1].strip()

            # Status
            ok = sample_rate == "16000" and channels == 1
            status = "✅" if ok else "⚠️ "
            print(f"  {status} {fname}")
            print(f"       Rate: {sample_rate}Hz  Channels: {channels}  Duration: {duration:.1f}s")
            print(f"       Volume: max={max_vol}  mean={mean_vol}")
            if sample_rate != "16000":
                print(f"       ⚠️  Expected 16000Hz — re-record or convert with ffmpeg")
            if int(channels) != 1:
                print(f"       ⚠️  Expected mono (1 channel)")
            print()
        except Exception as e:
            print(f"  ❌ {fname}: Error reading — {e}\n")

    if not found:
        print("  No WAV files found. Run: ./bin/record_golden.sh")


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoxInput WER Report Utilities")
    parser.add_argument("--check-audio", action="store_true",
                        help="Check audio quality of golden recordings")
    parser.add_argument("--recordings-dir",
                        default="tests/fixtures/golden/recordings",
                        help="Path to recordings directory")
    args = parser.parse_args()

    if args.check_audio:
        check_audio_quality(args.recordings_dir)
    else:
        parser.print_help()
