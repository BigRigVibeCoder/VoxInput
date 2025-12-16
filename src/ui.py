import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib, GObject
import threading
import os
import signal

# Constants
APP_ID = "com.voxinput.app"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "assets"))
ICON_IDLE = "icon_idle"
ICON_ACTIVE = "icon_active"

class SystemTrayApp:
    def __init__(self, toggle_callback, quit_callback, engine_change_callback=None):
        self.toggle_callback = toggle_callback
        self.quit_callback = quit_callback
        self.engine_change_callback = engine_change_callback
        self.is_listening = False
        
        # Create Indicator
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_IDLE,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_icon_theme_path(ASSETS_DIR)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self._build_menu()

    def _build_menu(self):
        menu = Gtk.Menu()
        
        # Toggle Item
        self.item_toggle = Gtk.MenuItem(label="Start Listening")
        self.item_toggle.connect('activate', self._on_toggle)
        menu.append(self.item_toggle)

        # Settings Item
        item_settings = Gtk.MenuItem(label="Settings")
        item_settings.connect('activate', self._on_settings)
        menu.append(item_settings)
        
        # Quit Item
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect('activate', self._on_quit)
        menu.append(item_quit)
        
        menu.show_all()
        self.indicator.set_menu(menu)

    def _on_toggle(self, _):
        self.toggle_callback()
        
    def _on_settings(self, _):
        dialog = SettingsDialog(self.engine_change_callback)
        dialog.run()
        dialog.destroy()

    def _on_quit(self, _):
        self.quit_callback()

    def set_listening_state(self, is_listening):
        self.is_listening = is_listening
        if is_listening:
            self.indicator.set_icon_full(ICON_ACTIVE, "Listening")
            GLib.idle_add(self.item_toggle.set_label, "Stop Listening")
        else:
            self.indicator.set_icon_full(ICON_IDLE, "Idle")
            GLib.idle_add(self.item_toggle.set_label, "Start Listening")

    def run(self):
        Gtk.main()

class SettingsDialog(Gtk.Dialog):
    def __init__(self, engine_change_callback=None):
        super().__init__(title="VoxInput Settings", flags=0)
        self.engine_change_callback = engine_change_callback
        self.set_default_size(500, 350)
        self.set_border_width(10)
        
        from .settings import SettingsManager
        self.settings = SettingsManager()
        
        content_area = self.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content_area.add(vbox)
        
        # --- Audio Device Section ---
        frame_device = Gtk.Frame(label="Audio Input")
        vbox.pack_start(frame_device, False, False, 0)
        
        grid_device = Gtk.Grid()
        grid_device.set_column_spacing(10)
        grid_device.set_row_spacing(10)
        grid_device.set_margin_top(10)
        grid_device.set_margin_bottom(10)
        grid_device.set_margin_start(10)
        grid_device.set_margin_end(10)
        frame_device.add(grid_device)
        
        lbl_device = Gtk.Label(label="Device:")
        lbl_device.set_halign(Gtk.Align.START)
        grid_device.attach(lbl_device, 0, 0, 1, 1)
        
        self.combo = Gtk.ComboBoxText()
        grid_device.attach(self.combo, 1, 0, 1, 1)
        
        # Populate devices
        try:
            from .pulseaudio_helper import get_pulseaudio_sources, filter_input_sources, get_default_source
            self.sources = filter_input_sources(get_pulseaudio_sources())
            
            # Try to get saved device, fallback to system default
            saved_device = self.settings.get("audio_device")
            current_default = get_default_source()
            target_device = saved_device if saved_device else current_default
            
            active_index = -1
            for i, source in enumerate(self.sources):
                self.combo.append_text(f"{source.description} ({source.name})")
                if source.name == target_device:
                    active_index = i
            
            if active_index != -1:
                self.combo.set_active(active_index)
            elif len(self.sources) > 0:
                self.combo.set_active(0)
                
            self.combo.connect("changed", self._on_device_changed)
            
        except ImportError:
            self.combo.append_text("Error: pulseaudio_helper not found")
            self.combo.set_sensitive(False)

        # --- Test Microphone Section ---
        lbl_test = Gtk.Label(label="Test Level:")
        lbl_test.set_halign(Gtk.Align.START)
        grid_device.attach(lbl_test, 0, 1, 1, 1)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_size_request(200, 10)
        grid_device.attach(self.level_bar, 1, 1, 1, 1)
        
        self.btn_test = Gtk.Button(label="Test")
        self.btn_test.connect("clicked", self._on_toggle_test)
        grid_device.attach(self.btn_test, 2, 1, 1, 1)
        
        # --- Engine / Model Section ---
        frame_model = Gtk.Frame(label="Speech Engine")
        vbox.pack_start(frame_model, False, False, 0)
        
        grid_model = Gtk.Grid()
        grid_model.set_column_spacing(10)
        grid_model.set_row_spacing(10)
        grid_model.set_margin_top(10)
        grid_model.set_margin_bottom(10)
        grid_model.set_margin_start(10)
        grid_model.set_margin_end(10)
        frame_model.add(grid_model)

        # Engine Type Selection
        lbl_engine = Gtk.Label(label="Engine Type:")
        lbl_engine.set_halign(Gtk.Align.START)
        grid_model.attach(lbl_engine, 0, 0, 1, 1)

        self.combo_engine = Gtk.ComboBoxText()
        self.combo_engine.append_text("Vosk")
        self.combo_engine.append_text("Whisper")
        
        saved_engine = self.settings.get("speech_engine", "Vosk")
        if saved_engine == "Whisper":
            self.combo_engine.set_active(1)
        else:
            self.combo_engine.set_active(0)
            
        self.combo_engine.connect("changed", self._on_engine_changed)
        grid_model.attach(self.combo_engine, 1, 0, 1, 1)
        
        # Vosk Settings
        self.lbl_vosk_path = Gtk.Label(label="Vosk Model Path:")
        self.lbl_vosk_path.set_halign(Gtk.Align.START)
        grid_model.attach(self.lbl_vosk_path, 0, 1, 1, 1)
        
        self.file_chooser = Gtk.FileChooserButton(title="Select Model Folder", action=Gtk.FileChooserAction.SELECT_FOLDER)
        saved_model = self.settings.get("model_path")
        if saved_model and os.path.exists(saved_model):
            self.file_chooser.set_filename(saved_model)
        else:
            default_model = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
            if os.path.exists(default_model):
                 self.file_chooser.set_current_folder(default_model)

        self.file_chooser.connect("file-set", self._on_model_set)
        grid_model.attach(self.file_chooser, 1, 1, 1, 1)

        # Whisper Settings
        self.lbl_whisper_size = Gtk.Label(label="Model Size:")
        self.lbl_whisper_size.set_halign(Gtk.Align.START)
        self.lbl_whisper_size.set_no_show_all(True) # Hidden by default if Vosk is active
        grid_model.attach(self.lbl_whisper_size, 0, 2, 1, 1)

        self.combo_whisper = Gtk.ComboBoxText()
        for size in ["tiny", "base", "small", "medium", "large"]:
            self.combo_whisper.append_text(size)
        
        saved_size = self.settings.get("whisper_model_size", "base")
        # Find index
        sizes = ["tiny", "base", "small", "medium", "large"]
        try:
            self.combo_whisper.set_active(sizes.index(saved_size))
        except ValueError:
            self.combo_whisper.set_active(1) # default base

        self.combo_whisper.connect("changed", self._on_whisper_size_changed)
        self.combo_whisper.set_no_show_all(True)
        grid_model.attach(self.combo_whisper, 1, 2, 1, 1)

        # -- Actions --
        # View Logs logic specifically requested in summary previously
        btn_logs = Gtk.Button(label="View Logs")
        btn_logs.connect("clicked", self._on_view_logs)
        vbox.pack_start(btn_logs, False, False, 0)

        self.is_testing = False
        self.test_stream = None
        self.pa = None
        
        # Trigger initial visibility state
        self._update_visibility()
        
        self.show_all()

    def _update_visibility(self):
        engine = self.combo_engine.get_active_text()
        if engine == "Vosk":
            self.lbl_vosk_path.show()
            self.file_chooser.show()
            self.lbl_whisper_size.hide()
            self.combo_whisper.hide()
        else:
            self.lbl_vosk_path.hide()
            self.file_chooser.hide()
            self.lbl_whisper_size.show()
            self.combo_whisper.show()

    def _on_engine_changed(self, combo):
        text = combo.get_active_text()
        if text:
            old_engine = self.settings.get("speech_engine")
            if old_engine != text:
                self.settings.set("speech_engine", text)
                self._update_visibility()
                if self.engine_change_callback:
                    self.engine_change_callback()

    def _on_whisper_size_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self.settings.set("whisper_model_size", text)

    def _on_device_changed(self, combo):
        idx = combo.get_active()
        if idx >= 0:
            source = self.sources[idx]
            from .pulseaudio_helper import set_default_source
            set_default_source(source.name)
            self.settings.set("audio_device", source.name)

    def _on_model_set(self, widget):
        path = widget.get_filename()
        if path:
            self.settings.set("model_path", path)
            
    def _on_view_logs(self, widget):
        from .config import LOG_FILE
        import subprocess
        try:
            subprocess.Popen(['xdg-open', LOG_FILE])
        except Exception as e:
            print(f"Failed to open logs: {e}")

    def _on_toggle_test(self, widget):
        if self.is_testing:
            self._stop_test()
            # _stop_test triggers playback which handles label reset
        else:
            self._start_test()
            widget.set_label("Stop")

    def _start_test(self):
        import pyaudio
        import audioop
        self.is_testing = True
        self.recorded_frames = []
        self.pa = pyaudio.PyAudio()
        
        # We need the correct device index for PyAudio that matches the PulseAudio default
        # But setting 'default' in PulseAudio usually makes PyAudio default input work.
        try:
            self.test_stream = self.pa.open(format=pyaudio.paInt16,
                                          channels=1,
                                          rate=16000,
                                          input=True,
                                          frames_per_buffer=1024)
            GLib.timeout_add(100, self._update_level)
        except Exception as e:
            print(f"Failed to start test stream: {e}")
            self.is_testing = False
            self.btn_test.set_label("Test")

    def _stop_test(self):
        self.is_testing = False
        if self.test_stream:
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None
        
        # Trigger Playback
        if hasattr(self, 'recorded_frames') and self.recorded_frames and self.pa:
            threading.Thread(target=self._play_playback, args=(self.recorded_frames, self.pa)).start()
            self.pa = None # Transferred to thread
            self.recorded_frames = []
        elif self.pa:
            self.pa.terminate()
            self.pa = None
            self.btn_test.set_label("Test")

    def _play_playback(self, frames, pa):
        import pyaudio
        GLib.idle_add(self.btn_test.set_label, "Playing...")
        GLib.idle_add(self.btn_test.set_sensitive, False)
        try:
             stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
             for fr in frames:
                 stream.write(fr)
             stream.stop_stream()
             stream.close()
        except Exception as e:
             print(f"Playback error: {e}")
        finally:
             pa.terminate()
             GLib.idle_add(self.btn_test.set_label, "Test")
             GLib.idle_add(self.btn_test.set_sensitive, True)

    def _update_level(self):
        if not self.is_testing or not self.test_stream:
            return False # Stop timer
        
        try:
            data = self.test_stream.read(1024, exception_on_overflow=False)
            self.recorded_frames.append(data)
            import audioop
            rms = audioop.rms(data, 2)
            # Normalize reasonably
            level = min(rms / 10000.0, 1.0) 
            self.level_bar.set_value(level)
        except Exception:
            pass
            
        return True

    def destroy(self):
        self._stop_test()
        super().destroy()


# Switch implementation below to GTK 3.0 safely
