
import fcntl
import os
import runpy
import signal
import subprocess
import sys

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Singleton lock ────────────────────────────────────────────────────────────
# Prevents multiple instances from running simultaneously.
# Lock file is in /tmp so it's auto-cleaned on reboot.
_LOCK_FILE = "/tmp/voxinput.lock"


def _kill_stale_instances():
    """Kill any stale VoxInput processes left behind by previous crashes or test runs.

    Prevents zombie processes from hogging the PulseAudio mic source,
    which causes the 'bright green, no text' failure.
    """
    import time

    my_pid = os.getpid()
    killed = []
    try:
        # Find all processes matching our patterns
        result = subprocess.run(
            ["pgrep", "-f", "VoxInput/run.py|VoxInput/src/main"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.strip().splitlines():
            pid = int(line.strip())
            if pid == my_pid:
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
            except ProcessLookupError:
                pass  # already dead
            except PermissionError:
                pass  # not ours

        # Also kill any orphaned xvfb-run wrappers from E2E tests
        result = subprocess.run(
            ["pgrep", "-f", "xvfb-run.*run.py"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.strip().splitlines():
            pid = int(line.strip())
            if pid == my_pid:
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
            except (ProcessLookupError, PermissionError):
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass  # pgrep not available or other issue — not fatal

    if killed:
        print(f"[VoxInput] Cleaned up {len(killed)} stale process(es): {killed}")
        # Wait for killed processes to actually exit so we can acquire
        # the singleton lock.  Without this, GNOME's desktop-icon
        # double-launch races: the second instance SIGTERMs the first,
        # but the dying process still holds the fcntl lock → both die.
        for _ in range(30):          # up to 3 s (30 × 0.1 s)
            still_alive = False
            for pid in killed:
                try:
                    os.kill(pid, 0)   # existence check
                    still_alive = True
                except ProcessLookupError:
                    pass
            if not still_alive:
                break
            time.sleep(0.1)

    # Release any stale lock file from a crashed instance
    if os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Check if that PID is still alive
            try:
                os.kill(old_pid, 0)  # signal 0 = existence check
            except ProcessLookupError:
                # Dead process — remove the stale lock
                os.remove(_LOCK_FILE)
                print(f"[VoxInput] Removed stale lock from dead PID {old_pid}")
        except (ValueError, OSError):
            # Corrupt lock file — remove it
            try:
                os.remove(_LOCK_FILE)
            except OSError:
                pass


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
    _kill_stale_instances()
    _lock_fd = _acquire_singleton()
    try:
        runpy.run_module('src.main', run_name='__main__', alter_sys=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

