#!/bin/bash
# Measure CPU and Memory usage of PipeWire under different loads

get_metrics() {
    # Get %CPU and RSS (KB) for pipewire and pipewire-pulse
    ps -C pipewire,pipewire-pulse -o %cpu,rss --no-headers | awk '{sum_cpu+=$1; sum_rss+=$2} END {print sum_cpu, sum_rss}'
}

echo "Measuring Baseline (10 seconds)..."
sleep 10
read cpu rss <<< $(get_metrics)
echo "Baseline: CPU=${cpu}%, Memory=$((rss/1024)) MB"

echo "Loading WebRTC..."
AEC_MOD=$(pactl load-module module-echo-cancel source_name=WebrtcPerf source_master=alsa_input.pci-0000_00_1f.3.analog-stereo aec_method=webrtc 2>/dev/null || echo "failed")
if [ "$AEC_MOD" != "failed" ]; then
    sleep 5 # stabilize
    echo "Measuring WebRTC (10 seconds)..."
    timeout 10 parecord --format=s16le --channels=1 --rate=16000 -d WebrtcPerf /dev/null &
    REC_PID=$!
    sleep 10
    kill $REC_PID 2>/dev/null || true
    read cpu rss <<< $(get_metrics)
    echo "WebRTC: CPU=${cpu}%, Memory=$((rss/1024)) MB"
    pactl unload-module $AEC_MOD
else
    echo "Failed to load WebRTC for test."
fi

echo "Loading RNNoise..."
RNN_MOD=$(pactl load-module module-ladspa-sink sink_name=RNNoisePerf master=alsa_output.pci-0000_00_1f.3.analog-stereo plugin=/usr/lib/ladspa/librnnoise_ladspa.so label=noise_suppressor_stereo 2>/dev/null || echo "failed")
if [ "$RNN_MOD" != "failed" ]; then
    sleep 5 # stabilize
    echo "Measuring RNNoise (10 seconds)..."
    timeout 10 paplay --device=RNNoisePerf tests/fixtures/golden/recordings/paragraph_a.wav &
    PLAY_PID=$!
    sleep 10
    kill $PLAY_PID 2>/dev/null || true
    read cpu rss <<< $(get_metrics)
    echo "RNNoise: CPU=${cpu}%, Memory=$((rss/1024)) MB"
    pactl unload-module $RNN_MOD
else
    echo "Failed to load RNNoise for test."
fi
