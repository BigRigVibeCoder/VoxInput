#!/bin/bash
# Fix VoxInput Hotkeys
# Run this if the Win+Shift+V shortcut stops working

echo "🔍 Checking Hotkey System..."

# 1. Check if the app is running
if pgrep -f "run.py" > /dev/null; then
    echo "✅ VoxInput App is running."
else
    echo "❌ VoxInput App is NOT running. Starting it..."
    cd "$(dirname "$0")/.."
    nohup venv/bin/python run.py > /dev/null 2>&1 &
    echo "   Started VoxInput."
fi

# 2. Check/Restart GNOME Settings Daemon (Media Keys)
if pgrep -x "gsd-media-keys" > /dev/null; then
    echo "✅ GNOME Media Keys Daemon is running."
else
    echo "⚠️ GNOME Media Keys Daemon is DEAD. Restarting..."
    /usr/libexec/gsd-media-keys &
    sleep 1
    if pgrep -x "gsd-media-keys" > /dev/null; then
        echo "   ✅ Successfully restarted daemon."
    else
        echo "   ❌ Failed to restart daemon. Try running: /usr/libexec/gsd-media-keys"
    fi
fi

# 3. Refresh bindings
echo "🔄 Refreshing keybindings..."
killall gsd-media-keys 2>/dev/null && /usr/libexec/gsd-media-keys &

echo ""
echo "✨ All fixed! Try pressing Win+Shift+V now."
