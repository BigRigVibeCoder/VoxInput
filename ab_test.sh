#!/bin/bash
set -e
GOLDEN="tests/fixtures/golden/recordings/paragraph_a.wav"

# Setup Null Sink
pactl load-module module-null-sink sink_name=VirtualMic sink_properties=device.description=VirtualMic > /tmp/sink_id
SINK_ID=$(cat /tmp/sink_id)
SOURCE="VirtualMic.monitor"

# Function to record while playing
record_test() {
    local NAME=$1
    local PLAY_SINK=$2
    echo "Testing $NAME on source $SOURCE, playing to $PLAY_SINK..."
    
    # Start recording in background (timeout just in case)
    timeout 20 parecord --format=s16le --channels=1 --rate=16000 -d $SOURCE "/tmp/ab_${NAME}.wav" &
    REC_PID=$!
    
    sleep 0.5
    # Play the golden recording 
    paplay --device=$PLAY_SINK $GOLDEN
    sleep 0.5
    kill $REC_PID || true
    wait $REC_PID 2>/dev/null || true
    echo "Saved /tmp/ab_${NAME}.wav"
}

# 1. Baseline
record_test "baseline" "VirtualMic"

# 2. RNNoise
RNN_MOD=$(pactl load-module module-ladspa-sink sink_name=RNNoise master=VirtualMic plugin=/usr/lib/ladspa/librnnoise_ladspa.so label=noise_suppressor_stereo rate=48000)
sleep 1
SOURCE="RNNoise.monitor"
record_test "rnnoise" "RNNoise"
pactl unload-module $RNN_MOD

# 3. WebRTC
SOURCE="VirtualMic.monitor"
AEC_MOD=$(pactl load-module module-echo-cancel source_name=WebrtcMic source_master=$SOURCE aec_method=webrtc aec_args="high_pass_filter=1 noise_suppression=1 analog_gain_control=1 digital_gain_control=1")
sleep 1
SOURCE="WebrtcMic"
record_test "webrtc" "VirtualMic"
pactl unload-module $AEC_MOD

# Cleanup
pactl unload-module $SINK_ID
echo "Audio generated in /tmp"
