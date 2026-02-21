# VoxInput Golden Test — Ground Truth
# =====================================
# READ THIS ALOUD during your recording session.
# Speak at a natural, comfortable dictation pace.
# Do NOT pause dramatically between sentences — be natural.
# This file is the permanent source of truth for WER testing.

## Paragraph A — Standard Accuracy Test

The weather forecast said there would be two inches of rain by four o'clock.
Their car broke down near the old library, so they had to walk through the park.
She said she could hear the music from here, but I wasn't so sure.
We need to buy flour, sugar, and eight eggs for the recipe.
The president met with senators from Colorado and New Mexico on Tuesday.
Please write your name, date of birth, and a brief description of the problem.
He ran quickly across the bridge, jumped over the fence, and disappeared into the night.

## Paragraph B — Numbers and Proper Nouns

Call me at five five five, one two three four between nine and five on weekdays.
The temperature dropped to thirty two degrees on the fifteenth of January.
Doctor Johnson prescribed four hundred milligrams twice a day for ten days.
Amazon, Google, and Microsoft reported record earnings in the third quarter.
The flight departs from terminal three at seven forty five in the morning.

## Paragraph C — Homophones and Tricky Words

I want to go to the store too if you are going there.
The knight knew the night would be long as he rode through the forest.
They're going to their house over there on the hill by the lake.
The principal principle is that every student deserves a fair chance to succeed.
She wore a blue dress to the gym where she blew out her knee doing squats.

## Paragraph D — Continuous Flow (Stress Test)

This is a continuous sentence designed to test how well the recognizer handles long uninterrupted speech without any natural pauses or sentence breaks because sometimes people talk in long run-on sentences when they are excited or in the middle of explaining something complex and the system needs to handle that gracefully without losing words or injecting garbage.

## Paragraph E — Voice Punctuation, Numbers, and Corrections

Dear mister Thompson comma I am writing to confirm your appointment on March twenty first at three forty five in the afternoon period new line The total cost is two hundred and fifteen dollars and sixty three cents semicolon please bring a valid photo ID period new line Can you meet me at twelve thirty question mark I need to discuss items one comma two comma and three before the deadline period new line Warning exclamation mark The system detected forty seven errors in section nine dash alpha colon please review immediately period new line He said quote I'll be there by five o'clock quote dash but honestly comma I wouldn't count on it period

---

## WER Acceptance Thresholds

| Engine           | Model            | Max WER | Notes                          |
|------------------|------------------|---------|--------------------------------|
| Vosk             | small (~40MB)    | 22%     | Default install                |
| Vosk             | large (~1.8GB)   | 10%     | Recommended for production     |
| Vosk             | gigaspeech       | 8%      | High-accuracy model            |
| Whisper          | tiny             | 15%     | Fastest, most errors           |
| Whisper          | base             | 8%      | Balanced                       |
| Whisper          | small            | 5%      | Recommended                    |
| Whisper          | medium           | 3%      | Near-human accuracy            |
| faster-whisper   | base (INT8)      | 8%      | Same accuracy, 4x faster       |
| faster-whisper   | large-v3-turbo   | 3%      | SOTA speed/accuracy            |

## Testing Paragraphs to Use Per Gate

| Gate   | Paragraphs        | Rationale                                         |
|--------|-------------------|---------------------------------------------------|
| Gate 1 | A only            | Establish Vosk baseline before any engine changes |
| Gate 2 | A + B             | Add numbers/proper nouns for Whisper accuracy     |
| Gate 3 | A + B + C         | Full homophone coverage tests spell correction    |
| Gate 4 | A + B + C + D     | Continuous flow tests silence detection tuning    |
| Gate 5 | A + B + C + D + E | Voice punctuation + number parsing + corrections  |
