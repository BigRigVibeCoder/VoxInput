import json
import wave
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tests.e2e.test_golden_e2e import transcribe_wav, parse_ground_truth, word_error_rate, normalize
from src.settings import SettingsManager

def main():
    gt = parse_ground_truth()
    ref = gt["A"]
    ref_norm = normalize(ref)
    
    results = {}
    for method in ["baseline", "rnnoise", "webrtc"]:
        wav_path = Path(f"/tmp/ab_{method}.wav")
        if not wav_path.exists():
            print(f"Missing {wav_path}")
            continue
            
        hypothesis = transcribe_wav(wav_path)
        hyp_norm = normalize(hypothesis)
        wer = word_error_rate(ref, hypothesis)
        results[method] = {
            "wer": wer,
            "hyp": hyp_norm
        }
        
        print(f"--- {method.upper()} ---")
        print(f"WER: {wer*100:.2f}%")
        print(f"HYP: {hyp_norm[:150]}...\n")
        
    print("--- SUMMARY ---")
    print(f"Baseline: {results.get('baseline', {}).get('wer', 1)*100:.2f}% WER")
    print(f"RNNoise:  {results.get('rnnoise', {}).get('wer', 1)*100:.2f}% WER")
    print(f"WebRTC:   {results.get('webrtc', {}).get('wer', 1)*100:.2f}% WER")
    
if __name__ == "__main__":
    main()
