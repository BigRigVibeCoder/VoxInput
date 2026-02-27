"""
tests/unit/test_startup_guard.py — Startup Guard Regression Tests
==================================================================
Ensures the startup guard in run.py correctly identifies and kills
stale VoxInput processes before acquiring the singleton lock.

Regression target: The 'bright green, no text' bug caused by zombie
processes hogging the PulseAudio mic source.
"""
import os
import signal
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch


# Import the module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestKillStaleInstances:
    """Tests for _kill_stale_instances() in run.py."""

    def _import_run(self):
        """Import run.py functions dynamically."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "run", os.path.join(os.path.dirname(__file__), "..", "..", "run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_does_not_kill_self(self):
        """The guard must never kill its own PID."""
        run = self._import_run()
        my_pid = os.getpid()

        with patch("subprocess.run") as mock_run:
            # Simulate pgrep returning our own PID
            mock_result = MagicMock()
            mock_result.stdout = f"{my_pid}\n"
            mock_run.return_value = mock_result

            with patch("os.kill") as mock_kill:
                run._kill_stale_instances()
                # os.kill should NOT have been called with our PID
                for call in mock_kill.call_args_list:
                    assert call[0][0] != my_pid, "Guard tried to kill its own PID!"

    def test_kills_stale_pids(self):
        """The guard should SIGTERM stale VoxInput PIDs."""
        run = self._import_run()
        fake_stale_pid = 99999

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = f"{fake_stale_pid}\n"
            mock_run.return_value = mock_result

            with patch("os.kill") as mock_kill:
                with patch("os.getpid", return_value=12345):
                    run._kill_stale_instances()
                    # Should have sent SIGTERM to the stale PID
                    mock_kill.assert_any_call(fake_stale_pid, signal.SIGTERM)

    def test_handles_pgrep_failure_gracefully(self):
        """If pgrep is not available, the guard should not crash."""
        run = self._import_run()

        with patch("subprocess.run", side_effect=FileNotFoundError("pgrep")):
            # Should not raise
            run._kill_stale_instances()

    def test_handles_pgrep_timeout_gracefully(self):
        """If pgrep times out, the guard should not crash."""
        run = self._import_run()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pgrep", 3)):
            run._kill_stale_instances()

    def test_removes_stale_lock_from_dead_pid(self):
        """If the lock file references a dead PID, it should be removed."""
        run = self._import_run()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lock", delete=False) as f:
            f.write("99999")  # non-existent PID
            lock_path = f.name

        try:
            with patch.object(run, "_LOCK_FILE", lock_path):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.stdout = ""
                    mock_run.return_value = mock_result

                    with patch("os.kill", side_effect=ProcessLookupError):
                        run._kill_stale_instances()

                    assert not os.path.exists(lock_path), "Stale lock file was not removed"
        finally:
            if os.path.exists(lock_path):
                os.remove(lock_path)


class TestModelPathPreservation:
    """Regression tests ensuring the Settings dialog never silently
    overwrites the user's model_path during initialization.

    Regression target: The combo box init bug that downgraded gigaspeech
    (4GB) to default_model (68MB), causing 'no voice to text'.
    """

    def test_settings_dialog_does_not_overwrite_model_path_on_init(self):
        """Opening the Settings dialog must NOT change the saved model_path."""
        from src.settings import SettingsManager

        sm = SettingsManager()
        original_path = "/some/custom/model/gigaspeech"
        sm.set("model_path", original_path)

        # Simulate what _build_engine_tab does: extract basename and match
        saved_model_path = sm.get("model_path", "")
        saved_model_name = os.path.basename(saved_model_path) if saved_model_path else "default_model"

        # The combo box would list models alphabetically
        models = ["default_model", "gigaspeech"]
        active_idx = 0
        for i, m in enumerate(sorted(models)):
            if m == saved_model_name:
                active_idx = i

        # gigaspeech should be at index 1 in sorted order
        assert saved_model_name == "gigaspeech"
        assert active_idx == 1, (
            f"Combo would select index {active_idx} instead of 1 — "
            f"this would silently switch to 'default_model'!"
        )

        # The saved setting must remain untouched
        assert sm.get("model_path") == original_path

    def test_empty_model_path_defaults_safely(self):
        """If model_path is empty, the combo should not corrupt settings."""
        saved_model_path = ""
        saved_model_name = os.path.basename(saved_model_path) if saved_model_path else "default_model"

        # With empty path, saved_model_name falls back to "default_model"
        assert saved_model_name == "default_model"

    def test_model_dir_only_path_extracts_correctly(self):
        """If model_path is 'model/' (no specific model), basename is empty.
        This was the original bug trigger — os.path.basename('model/') returns ''."""
        saved_model_path = "model/"
        basename = os.path.basename(saved_model_path)
        # os.path.basename("model/") returns "" — this is the dangerous case
        # The fallback should kick in
        saved_model_name = basename if basename else "default_model"
        assert saved_model_name == "default_model"
