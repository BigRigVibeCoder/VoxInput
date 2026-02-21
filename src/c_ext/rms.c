/*
 * src/c_ext/rms.c — VoxInput ctypes C extension
 * =================================================
 * Fast RMS computation for int16 PCM audio samples.
 * Single-pass, no Python overhead, no intermediate array allocation.
 *
 * Build (via build.sh or install.sh):
 *   gcc -O3 -march=native -shared -fPIC -o librms.so rms.c -lm
 *
 * Python usage (see src/c_ext/__init__.py):
 *   from src.c_ext import rms_int16
 *   level = rms_int16(data_bytes)    # data_bytes: raw PCM int16 bytes
 */

#include <stdint.h>
#include <math.h>

/*
 * vox_rms_int16 — compute RMS of n int16 PCM samples in one pass.
 *
 * Args:
 *   samples  — pointer to int16 PCM buffer (raw bytes from PyAudio callback)
 *   n        — number of samples (len(bytes) // 2)
 *
 * Returns:
 *   RMS value as double (same units as numpy int16 range, 0–32767)
 */
double vox_rms_int16(const int16_t* samples, int n) {
    if (n <= 0) return 0.0;
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        double s = (double)samples[i];
        sum += s * s;
    }
    return sqrt(sum / (double)n);
}

/*
 * vox_pcm_to_float32 — convert int16 PCM directly to normalized float32.
 * Eliminates python loop/numpy cast overhead for Whisper transcription.
 *
 * Args:
 *   samples  — pointer to continuous int16 input array
 *   out      — pointer to pre-allocated float32 output array
 *   n        — number of samples to process
 */
void vox_pcm_to_float32(const int16_t* samples, float* out, int n) {
    if (n <= 0) return;
    for (int i = 0; i < n; i++) {
        out[i] = (float)samples[i] / 32768.0f;
    }
}
