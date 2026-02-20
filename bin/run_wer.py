#!/usr/bin/env python3
"""
Standalone golden WER test — bypasses pytest conftest vosk mock.
Feeds .raw PCM files directly to real Vosk and measures WER.

Usage: python3 bin/run_wer.py
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vosk import KaldiRecognizer, Model

RECORDINGS = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "golden", "recordings")
GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "golden", "ground_truth.md")
MODEL_PATH = "/home/bdavidriggins/Documents/VoxInput/model/gigaspeech"
CHUNK = 3200 * 2  # 200ms @ 16kHz × 2 bytes/sample int16

# ─── Ground Truth Parser ───────────────────────────────────────────────────────

def load_ground_truth() -> dict:
    paragraphs, label, lines = {}, None, []
    with open(GROUND_TRUTH_FILE) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r'^## Paragraph ([A-D])', line)
            if m:
                if label: paragraphs[label] = ' '.join(lines).strip()
                label, lines = m.group(1), []
                continue
            if '## WER Acceptance' in line or '## Testing' in line: break
            if label and line and not line.startswith('#'):
                lines.append(line.strip())
    if label and lines: paragraphs[label] = ' '.join(lines).strip()
    return paragraphs

def normalize(text: str) -> str:
    """Lowercase, strip punctuation for fair WER comparison."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", ' ', text)
    return ' '.join(text.split())


# ─── Simple WER ────────────────────────────────────────────────────────────

def wer(ref: str, hyp: str) -> float:
    r, h = ref.lower().split(), hyp.lower().split()
    if not r:
        return 0.0
    d = [[0]*(len(h)+1) for _ in range(len(r)+1)]
    for i in range(len(r)+1): d[i][0]=i
    for j in range(len(h)+1): d[0][j]=j
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            d[i][j] = d[i-1][j-1] if r[i-1]==h[j-1] else 1+min(d[i-1][j], d[i][j-1], d[i-1][j-1])
    return d[len(r)][len(h)] / len(r)

# ─── Transcription ─────────────────────────────────────────────────────────

def transcribe(path: str, model: Model) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)
    words, committed = [], []
    for i in range(0, len(raw), CHUNK):
        chunk = raw[i:i+CHUNK]
        if not chunk:
            continue
        if rec.AcceptWaveform(chunk):
            text = json.loads(rec.Result()).get("text", "").split()
            words.extend(text[len(committed):]); committed=[]
        else:
            partial = json.loads(rec.PartialResult()).get("partial","").split()
            stable = max(0, len(partial)-1)
            if stable > len(committed):
                new = partial[len(committed):stable]
                words.extend(new); committed.extend(new)
    final = json.loads(rec.FinalResult()).get("text","").split()
    words.extend(final[len(committed):])
    return " ".join(words)

# ─── Ground truth (simplified normalize) ───────────────────────────────────

GROUND_TRUTH = load_ground_truth()
WER_THRESHOLD = 0.08   # 8% — Vosk gigaspeech target per ground_truth.md

# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"VoxInput Golden WER Test — Vosk Gigaspeech")
    print(f"Model: {MODEL_PATH}")
    print(f"{'='*60}")

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model path not found: {MODEL_PATH}")
        sys.exit(1)

    t_load = time.perf_counter()
    print("Loading model (gigaspeech is large — may take 30s)...")
    model = Model(MODEL_PATH)
    print(f"Model loaded in {time.perf_counter()-t_load:.1f}s\n")

    results = {}
    for label in ["A", "B", "C", "D"]:
        path = os.path.join(RECORDINGS, f"paragraph_{label.lower()}.raw")
        if not os.path.exists(path):
            print(f"  Paragraph {label}: SKIPPED (no file)")
            continue
        if label not in GROUND_TRUTH:
            print(f"  Paragraph {label}: SKIPPED (no ground truth)")
            continue

        t0 = time.perf_counter()
        hyp = transcribe(path, model)
        elapsed = time.perf_counter() - t0
        ref = GROUND_TRUTH[label]
        ref_n = normalize(ref)
        hyp_n = normalize(hyp)
        score = wer(ref_n, hyp_n)
        status = "✅ PASS" if score <= WER_THRESHOLD else "❌ FAIL"

        print(f"Paragraph {label} [{elapsed:.1f}s] WER={score:.1%} {status}")
        print(f"  REF: {ref_n[:110]}")
        print(f"  HYP: {hyp_n[:110]}")
        print()
        results[label] = score

    if results:
        avg = sum(results.values()) / len(results)
        overall = "✅ GATE PASS" if avg <= WER_THRESHOLD else "❌ GATE FAIL"
        print(f"{'='*60}")
        print(f"AVERAGE WER: {avg:.1%}  {overall}")
        print(f"{'='*60}\n")
        sys.exit(0 if avg <= WER_THRESHOLD else 1)

if __name__ == "__main__":
    main()
