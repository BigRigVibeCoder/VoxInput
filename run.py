
import fcntl
import os
import runpy
import sys

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Singleton lock ────────────────────────────────────────────────────────────
# Prevents multiple instances from running simultaneously.
# Lock file is in /tmp so it's auto-cleaned on reboot.
_LOCK_FILE = "/tmp/voxinput.lock"

def _acquire_singleton():
    """Try to get an exclusive lock. Exits with message if another instance is running."""
    try:
        lock = open(_LOCK_FILE, "w")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID so toggle.sh / diagnostics can find us
        lock.write(str(os.getpid()))
        lock.flush()
        return lock   # keep fd open — lock released when process exits
    except BlockingIOError:
        print("VoxInput is already running. Use the tray icon or Super+Shift+V to toggle.")
        sys.exit(0)

if __name__ == "__main__":
    _lock_fd = _acquire_singleton()
    try:
        runpy.run_module('src.main', run_name='__main__', alter_sys=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
