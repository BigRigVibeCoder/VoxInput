# Recording Session Instructions
# ================================
# Do this ONCE. Your recording becomes the permanent test fixture.

## Before You Record

1. Find a quiet room (close doors, turn off fans)
2. Sit 12–18 inches from your microphone
3. Make sure VoxInput is NOT running (it will compete for the mic)
4. Read the paragraphs in `ground_truth.md` out loud a few times to warm up

## Recording Command

Run the capture harness — it will guide you through the session:

```bash
./bin/record_golden.sh
```

This script will:
  - List your available microphones (pick the one you normally use)
  - Count you in (3... 2... 1...)
  - Record each paragraph separately
  - Play each recording back so you can verify quality
  - Save everything to `tests/fixtures/golden/recordings/`
  - Generate a session report

## Manual Alternative

If you prefer to record manually:

```bash
# Paragraph A
arecord -d 30 -f S16_LE -r 16000 -c 1 \
  tests/fixtures/golden/recordings/paragraph_a.wav

# Paragraph B
arecord -d 25 -f S16_LE -r 16000 -c 1 \
  tests/fixtures/golden/recordings/paragraph_b.wav

# Paragraph C
arecord -d 30 -f S16_LE -r 16000 -c 1 \
  tests/fixtures/golden/recordings/paragraph_c.wav

# Paragraph D (continuous flow — this one is longer)
arecord -d 40 -f S16_LE -r 16000 -c 1 \
  tests/fixtures/golden/recordings/paragraph_d.wav
```

## Quality Check

After recording, run:

```bash
python3 tests/golden/wer_report.py --check-audio
```

This will:
  - Verify sample rate is 16kHz mono
  - Check audio levels (warn if too quiet or clipped)
  - Play back excerpts for your review

## Recording Tips

| ✅ DO                              | ❌ DON'T                              |
|------------------------------------|---------------------------------------|
| Speak at your normal dictation pace | Rush through the text                 |
| Pause naturally between sentences  | Add dramatic theatrical pauses        |
| Say contractions naturally (won't) | Over-enunciate robotically            |
| Re-record if you stumble           | Keep a recording with major errors    |
| Use the same mic as daily use      | Use phone or laptop mic if you use USB|

## After Recording

Commit your recordings:

```bash
git add tests/fixtures/golden/recordings/
git commit -m "test: Add golden voice recordings for WER baseline"
```

> **Note**: WAV files are large. Consider adding to Git LFS:
> `git lfs track "*.wav"` before committing.
