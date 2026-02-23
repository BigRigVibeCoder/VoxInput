#!/usr/bin/env python3
"""
bin/run_ptt_pipeline.py — Golden recording PTT pipeline test
=============================================================
Simulates a push-to-talk session: feeds golden .raw recordings through
the FULL PTT correction pipeline and compares output quality.

Pipeline:  Vosk transcribe → spell.correct() → fix_homophones() → voice punctuation

Shows side-by-side comparison:
  - RAW:  what Vosk produces (streaming, no correction)
  - PTT:  full-context corrected output (what PTT mode injects)
  - REF:  ground truth

Reports WER for both modes so we can measure the improvement.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vosk import KaldiRecognizer, Model

RECORDINGS = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "golden", "recordings")
GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "golden", "ground_truth.md")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "gigaspeech")
CHUNK = 3200 * 2  # 200ms @ 16kHz


# ─── Ground Truth ─────────────────────────────────────────────────────────

def load_ground_truth() -> dict:
    paragraphs, label, lines = {}, None, []
    with open(GROUND_TRUTH_FILE) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r'^## Paragraph ([A-E])', line)
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
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", ' ', text)
    return ' '.join(text.split())


# Digits→words map for fair WER comparison (ParseNum is correct for dictation)
_DIGIT_WORDS = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
    '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
}

def normalize_digits(text: str) -> str:
    """Normalize text, converting isolated digits back to words for WER fairness."""
    text = normalize(text)
    # Convert ordinals: 21st→twenty first, 15th→fifteenth (rough — just strip suffix)
    text = re.sub(r'\b(\d+)(st|nd|rd|th)\b', lambda m: m.group(1), text)
    # Convert isolated digits to words
    tokens = []
    for tok in text.split():
        if tok in _DIGIT_WORDS:
            tokens.append(_DIGIT_WORDS[tok])
        else:
            tokens.append(tok)
    return ' '.join(tokens)


def wer(ref: str, hyp: str) -> float:
    r, h = ref.lower().split(), hyp.lower().split()
    if not r: return 0.0
    d = [[0]*(len(h)+1) for _ in range(len(r)+1)]
    for i in range(len(r)+1): d[i][0]=i
    for j in range(len(h)+1): d[0][j]=j
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            d[i][j] = d[i-1][j-1] if r[i-1]==h[j-1] else 1+min(d[i-1][j], d[i][j-1], d[i-1][j-1])
    return d[len(r)][len(h)] / len(r)


# ─── Vosk Transcription (simulates PTT session) ───────────────────────────

def transcribe_raw(path: str, model: Model) -> str:
    """Feed raw PCM through Vosk, return the raw transcript (no correction)."""
    with open(path, "rb") as f:
        raw = f.read()
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    # Feed all chunks (simulates holding PTT key)
    for i in range(0, len(raw), CHUNK):
        chunk = raw[i:i+CHUNK]
        if chunk:
            rec.AcceptWaveform(chunk)

    # Finalize (simulates releasing PTT key)
    result = json.loads(rec.FinalResult())
    return result.get("text", "")


def apply_ptt_pipeline(raw_text: str) -> str:
    """Run the full PTT correction pipeline on a transcript."""
    from src.settings import SettingsManager
    from src.spell_corrector import SpellCorrector
    from src.homophones import fix_homophones
    from src.injection import apply_voice_punctuation

    settings = SettingsManager()
    spell = SpellCorrector(settings)

    # Step 1: Spell correction (full sentence context)
    corrected = spell.correct(raw_text)
    # Step 2: Homophone resolution (full sentence context)
    corrected = fix_homophones(corrected)
    # Step 3: Voice punctuation
    corrected = apply_voice_punctuation(corrected)

    return corrected


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    GROUND_TRUTH = load_ground_truth()

    print(f"\n{'='*70}")
    print(f"VoxInput PTT Pipeline Test — Full-Context vs Raw")
    print(f"Model: {MODEL_PATH}")
    print(f"{'='*70}")

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found: {MODEL_PATH}")
        sys.exit(1)

    print("Loading gigaspeech model...")
    t0 = time.perf_counter()
    model = Model(MODEL_PATH)
    print(f"Model loaded in {time.perf_counter()-t0:.1f}s\n")

    raw_wers, ptt_wers, norm_wers = {}, {}, {}

    for label in sorted(GROUND_TRUTH.keys()):
        path = os.path.join(RECORDINGS, f"paragraph_{label.lower()}.raw")
        if not os.path.exists(path):
            print(f"  Paragraph {label}: SKIPPED (no recording)")
            continue

        ref = GROUND_TRUTH[label]
        ref_n = normalize(ref)

        # 1. Get raw Vosk transcript
        t1 = time.perf_counter()
        raw_text = transcribe_raw(path, model)
        t_vosk = time.perf_counter() - t1

        # 2. Run through full PTT correction pipeline
        t2 = time.perf_counter()
        ptt_text = apply_ptt_pipeline(raw_text)
        t_pipe = time.perf_counter() - t2

        raw_n = normalize(raw_text)
        ptt_n = normalize(ptt_text)
        ptt_digits_n = normalize_digits(ptt_text)  # digits→words for fair comparison

        raw_score = wer(ref_n, raw_n)
        ptt_score = wer(ref_n, ptt_n)
        norm_score = wer(ref_n, ptt_digits_n)

        raw_wers[label] = raw_score
        ptt_wers[label] = ptt_score
        norm_wers[label] = norm_score

        delta = raw_score - norm_score
        arrow = "⬆️  IMPROVED" if delta > 0.001 else ("➡️  SAME" if abs(delta) <= 0.001 else "⬇️  REGRESSED")

        print(f"── Paragraph {label} ─────────────────────────────────")
        print(f"  Vosk:  {t_vosk:.1f}s  |  Pipeline: {t_pipe:.3f}s")
        print(f"  RAW WER:  {raw_score:.1%}")
        print(f"  PTT WER:  {ptt_score:.1%}  (digits as-is)")
        print(f"  PTT NORM: {norm_score:.1%}  (digits→words)  {arrow} ({delta:+.1%})")
        print(f"  REF: {ref_n[:100]}")
        print(f"  RAW: {raw_n[:100]}")
        print(f"  PTT: {ptt_n[:100]}")
        print()

    if raw_wers:
        avg_raw = sum(raw_wers.values()) / len(raw_wers)
        avg_ptt = sum(ptt_wers.values()) / len(ptt_wers)
        avg_norm = sum(norm_wers.values()) / len(norm_wers)

        print(f"{'='*70}")
        print(f"  RAW AVG WER:   {avg_raw:.1%}  (Vosk only)")
        print(f"  PTT AVG WER:   {avg_ptt:.1%}  (full pipeline, digits as-is)")
        print(f"  PTT NORM WER:  {avg_norm:.1%}  (full pipeline, digits→words)")
        delta = avg_raw - avg_norm
        status = "✅ NO REGRESSION" if avg_norm <= avg_raw + 0.005 else "❌ REGRESSION"
        print(f"  DELTA:         {delta:+.1%}  {status}")
        print(f"{'='*70}\n")

        # Pass if PTT-NORM doesn't regress more than 0.5% from RAW
        sys.exit(0 if avg_norm <= avg_raw + 0.005 else 1)


if __name__ == "__main__":
    main()
