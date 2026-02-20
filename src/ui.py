import os
import threading

import gi

gi.require_version('Gtk', '3.0')
import cairo  # noqa: E402  (for OSD waveform)
from gi.repository import GLib, Gtk, Gdk, Pango, PangoCairo  # noqa: E402

# Constants
APP_ID = "com.voxinput.app"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "assets"))
ICON_IDLE = "icon_idle"
ICON_ACTIVE = "icon_active"


# ──────────────────────────────────────────────────────────────
# OSD Overlay (Phase 5) — floating borderless window
# Renders recognized text + audio level bar at bottom-right of screen
# ──────────────────────────────────────────────────────────────

class OSDOverlay(Gtk.Window):
    """
    Floating on-screen display.  Shows the current recognition text
    and a live audio level bar while dictating.

    Usage:
        osd = OSDOverlay()
        osd.set_text("hello world")   # called from recognizer thread via GLib.idle_add
        osd.set_level(0.4)            # called every audio chunk
        osd.show()  / osd.hide()
    """
    _WIDTH  = 520
    _HEIGHT = 70
    _MARGIN = 18   # px from screen edge

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)

        # RGBA (transparency)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self._text  = ""
        self._level = 0.0
        self._pos_set = False

        draw_area = Gtk.DrawingArea()
        draw_area.set_size_request(self._WIDTH, self._HEIGHT)
        draw_area.connect("draw", self._on_draw)
        self.add(draw_area)
        self._draw_area = draw_area

        self.set_default_size(self._WIDTH, self._HEIGHT)
        self._update_position()

    # ─ Public API ──────────────────────────────────────────

    def set_text(self, text: str):
        self._text = text
        GLib.idle_add(self._draw_area.queue_draw)

    def set_level(self, level: float):
        """level: 0.0 – 1.0"""
        self._level = max(0.0, min(1.0, level))
        GLib.idle_add(self._draw_area.queue_draw)

    # ─ Internal ─────────────────────────────────────────

    def _update_position(self):
        """Position bottom-right of the primary monitor."""
        display  = Gdk.Display.get_default()
        monitor  = display.get_primary_monitor() if display else None
        if monitor:
            geo = monitor.get_geometry()
            x = geo.x + geo.width  - self._WIDTH  - self._MARGIN
            y = geo.y + geo.height - self._HEIGHT - self._MARGIN
            self.move(x, y)

    def _on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r  = 12.0   # corner radius

        # ─ Background: semi-transparent dark pill ─
        cr.new_sub_path()
        cr.arc(r,     r,     r, 3.14, 2.70)
        cr.arc(w - r, r,     r, 4.71, 0.0)
        cr.arc(w - r, h - r, r, 0.0,  1.57)
        cr.arc(r,     h - r, r, 1.57, 3.14)
        cr.close_path()
        cr.set_source_rgba(0.05, 0.05, 0.10, 0.82)
        cr.fill()

        # ─ Mic level bar (thin, bottom, cyan) ─
        bar_h  = 4
        bar_y  = h - bar_h - 4
        bar_w  = max(4, int((w - 20) * self._level))
        cr.set_source_rgba(0.0, 0.85, 0.95, 0.9)
        cr.rectangle(10, bar_y, bar_w, bar_h)
        cr.fill()

        # ─ Text ─
        if self._text:
            layout = PangoCairo.create_layout(cr)
            font   = Pango.FontDescription.from_string("Sans Bold 14")
            layout.set_font_description(font)
            layout.set_text(self._text[-80:], -1)   # last 80 chars
            layout.set_width((w - 20) * Pango.SCALE)
            layout.set_ellipsize(Pango.EllipsizeMode.START)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.move_to(10, (h - bar_h - 8 - th) / 2)
            PangoCairo.show_layout(cr, layout)

        # ─ Mic icon dot (left side, green when active) ─
        dot_color = (0.15, 0.9, 0.45) if self._level > 0.05 else (0.5, 0.5, 0.5)
        cr.set_source_rgb(*dot_color)
        cr.arc(w - 16, 16, 5, 0, 6.28)
        cr.fill()


class SystemTrayApp:
    def __init__(self, toggle_callback, quit_callback, engine_change_callback=None):
        self.toggle_callback = toggle_callback
        self.quit_callback = quit_callback
        self.engine_change_callback = engine_change_callback
        self.is_listening = False

        # P5: OSD overlay — hidden until listening starts
        self.osd = OSDOverlay()

        # Create StatusIcon (replaces AppIndicator3)
        self.icon = Gtk.StatusIcon()
        self.icon.set_from_file(os.path.join(ASSETS_DIR, f"{ICON_IDLE}.svg"))
        self.icon.set_tooltip_text("VoxInput (Idle)")
        
        # Connect Signals
        self.icon.connect('activate', self._on_left_click)
        self.icon.connect('popup-menu', self._on_right_click)
        
        # We don't build the menu once and attach it like AppIndicator.
        # Instead we build/show it on demand in _on_right_click, 
        # or we can keep a persistent one. Let's keep a persistent one for efficiency.
        self.menu = self._build_menu()

    def _build_menu(self):
        menu = Gtk.Menu()
        
        # Toggle Item (kept in menu as backup)
        self.item_toggle = Gtk.MenuItem(label="Start Listening")
        self.item_toggle.connect('activate', self._on_toggle_menu)
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
        return menu

    def _on_left_click(self, icon):
        # Toggle listening state directly
        self.toggle_callback()

    def _on_right_click(self, icon, button, time):
        # Show menu
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

    def _on_toggle_menu(self, _):
        # Callback from menu item
        self.toggle_callback()
        
    def _on_settings(self, _):
        dialog = SettingsDialog(self.engine_change_callback)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.save_settings()
        dialog.destroy()

    def _on_quit(self, _):
        self.quit_callback()

    def set_listening_state(self, is_listening):
        self.is_listening = is_listening
        if is_listening:
            self.icon.set_from_file(os.path.join(ASSETS_DIR, f"{ICON_ACTIVE}.svg"))
            self.icon.set_tooltip_text("VoxInput (Listening)")
            GLib.idle_add(self.item_toggle.set_label, "Stop Listening")
            GLib.idle_add(self.osd.show_all)   # P5: show OSD
        else:
            self.icon.set_from_file(os.path.join(ASSETS_DIR, f"{ICON_IDLE}.svg"))
            self.icon.set_tooltip_text("VoxInput (Idle)")
            GLib.idle_add(self.item_toggle.set_label, "Start Listening")
            GLib.idle_add(self.osd.hide)        # P5: hide OSD
            GLib.idle_add(self.osd.set_text, "")

    def update_osd(self, text: str, level: float = 0.0):
        """Called from main.py injection thread to update the OSD in real-time."""
        self.osd.set_text(text)
        self.osd.set_level(level)

    def run(self):
        Gtk.main()

class SettingsDialog(Gtk.Dialog):
    def __init__(self, engine_change_callback=None):
        super().__init__(title="VoxInput Settings", flags=0)
        self.engine_change_callback = engine_change_callback
        self.set_default_size(500, 500)
        self.set_border_width(10)
        
        from .settings import SettingsManager
        self.settings = SettingsManager()
        # Copy current settings to temp dict for modification
        self.temp_settings = self.settings.settings.copy()
        
        # Add Action Buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)
        
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
            from .pulseaudio_helper import filter_input_sources, get_default_source, get_pulseaudio_sources
            self.sources = filter_input_sources(get_pulseaudio_sources())
            
            # Try to get saved device, fallback to system default
            saved_device = self.temp_settings.get("audio_device")
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
        
        saved_engine = self.temp_settings.get("speech_engine", "Vosk")
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
        
        self.file_chooser = Gtk.FileChooserButton(
            title="Select Model Folder", 
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        saved_model = self.temp_settings.get("model_path")
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
        grid_model.attach(self.lbl_whisper_size, 0, 2, 1, 1)

        self.combo_whisper = Gtk.ComboBoxText()
        WHISPER_SIZES = ["tiny", "base", "small", "medium", "large",
                         "large-v3-turbo", "distil-large-v3"]  # P2-04: SOTA models
        for size in WHISPER_SIZES:
            self.combo_whisper.append_text(size)

        saved_size = self.temp_settings.get("whisper_model_size", "base")
        try:
            self.combo_whisper.set_active(WHISPER_SIZES.index(saved_size))
        except ValueError:
            self.combo_whisper.set_active(1)  # default base

        self.combo_whisper.connect("changed", self._on_whisper_size_changed)
        grid_model.attach(self.combo_whisper, 1, 2, 1, 1)

        # --- Advanced Settings (Shared) ---
        self.frame_adv = Gtk.Frame(label="Advanced Options")
        vbox.pack_start(self.frame_adv, False, False, 0)
        
        grid_adv = Gtk.Grid()
        grid_adv.set_column_spacing(10)
        grid_adv.set_row_spacing(10)
        grid_adv.set_margin_top(10)
        grid_adv.set_margin_bottom(10)
        grid_adv.set_margin_start(10)
        grid_adv.set_margin_end(10)
        self.frame_adv.add(grid_adv)
        
        # Silence Duration
        lbl_silence = Gtk.Label(label="Pause after speech (seconds):")
        lbl_silence.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_silence, 0, 0, 1, 1)
        
        self.spin_silence = Gtk.SpinButton.new_with_range(0.1, 5.0, 0.1)
        self.spin_silence.set_value(self.temp_settings.get("silence_duration", 0.6))
        self.spin_silence.connect(
            "value-changed", 
            lambda w: self._set_temp("silence_duration", round(w.get_value(), 2))
        )
        grid_adv.attach(self.spin_silence, 1, 0, 1, 1)
        
        lbl_silence_desc = Gtk.Label()
        lbl_silence_desc.set_markup(
            "<small><i>How long to wait for silence before finalizing.\n"
            "Default: 0.6s. Range: 0.1 - 2.0s.\n"
            "Lower = Snappier response. Higher = Allows longer pauses.</i></small>"
        )
        lbl_silence_desc.set_line_wrap(True)
        lbl_silence_desc.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_silence_desc, 0, 1, 2, 1)

        # Spacer
        grid_adv.attach(Gtk.Label(label=""), 0, 2, 2, 1)

        # Whisper Lag
        lbl_lag = Gtk.Label(label="Stability Lag (words):")
        lbl_lag.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_lag, 0, 3, 1, 1)
        
        self.spin_lag = Gtk.SpinButton.new_with_range(0, 10, 1)
        self.spin_lag.set_value(self.temp_settings.get("stability_lag", 2))
        self.spin_lag.connect("value-changed", lambda w: self._set_temp("stability_lag", int(w.get_value())))
        grid_adv.attach(self.spin_lag, 1, 3, 1, 1)
        
        lbl_lag_desc = Gtk.Label()
        lbl_lag_desc.set_markup(
            "<small><i>Number of words to hold back to prevent flickering.\n"
            "Default: 2. Range: 0 - 5.\n"
            "Increase if text changes frequently while speaking.</i></small>"
        )
        lbl_lag_desc.set_line_wrap(True)
        lbl_lag_desc.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_lag_desc, 0, 4, 2, 1)

        # Spacer
        grid_adv.attach(Gtk.Label(label=""), 0, 5, 2, 1)
        
        # Silence Threshold
        lbl_thresh = Gtk.Label(label="Mic Noise Threshold:")
        lbl_thresh.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_thresh, 0, 6, 1, 1)
        
        self.spin_thresh = Gtk.SpinButton.new_with_range(0, 5000, 100)
        self.spin_thresh.set_value(self.temp_settings.get("silence_threshold", 500))
        self.spin_thresh.connect("value-changed", lambda w: self._set_temp("silence_threshold", int(w.get_value())))
        grid_adv.attach(self.spin_thresh, 1, 6, 1, 1)

        lbl_thresh_desc = Gtk.Label()
        lbl_thresh_desc.set_markup(
            "<small><i>Volume level required to detect speech.\n"
            "Default: 500. Range: 100 - 3000.\n"
            "Increase if background noise triggers random typing.</i></small>"
        )
        lbl_thresh_desc.set_line_wrap(True)
        lbl_thresh_desc.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_thresh_desc, 0, 7, 2, 1)

        # Spacer
        grid_adv.attach(Gtk.Label(label=""), 0, 8, 2, 1)

        # Speed Mode Toggle (P1-03)
        self.check_fast_mode = Gtk.CheckButton(
            label="⚡ Speed Mode (LAG=0 — instant output, may reduce accuracy)"
        )
        self.check_fast_mode.set_active(self.temp_settings.get("fast_mode", False))
        self.check_fast_mode.connect(
            "toggled", lambda w: self._set_temp("fast_mode", w.get_active())
        )
        grid_adv.attach(self.check_fast_mode, 0, 9, 2, 1)

        lbl_fast_desc = Gtk.Label()
        lbl_fast_desc.set_markup(
            "<small><i>Bypasses stability lag — words appear as you speak.\n"
            "Best for Vosk. For Whisper, combine with tiny/base model.</i></small>"
        )
        lbl_fast_desc.set_line_wrap(True)
        lbl_fast_desc.set_halign(Gtk.Align.START)
        grid_adv.attach(lbl_fast_desc, 0, 10, 2, 1)

        # --- Microphone Enhancement Tab (Phase 6 UI) ---
        frame_mic = Gtk.Frame(label="🎤  Microphone Enhancement")
        vbox.pack_start(frame_mic, False, False, 0)

        grid_mic = Gtk.Grid()
        grid_mic.set_column_spacing(10)
        grid_mic.set_row_spacing(10)
        grid_mic.set_margin_top(10)
        grid_mic.set_margin_bottom(10)
        grid_mic.set_margin_start(10)
        grid_mic.set_margin_end(10)
        frame_mic.add(grid_mic)

        # Input Volume
        lbl_vol = Gtk.Label(label="Input Volume:")
        lbl_vol.set_halign(Gtk.Align.START)
        grid_mic.attach(lbl_vol, 0, 0, 1, 1)

        self.spin_volume = Gtk.SpinButton.new_with_range(50, 150, 5)
        self.spin_volume.set_value(self.temp_settings.get("mic_volume", 100))
        self.spin_volume.connect(
            "value-changed", lambda w: self._set_temp("mic_volume", int(w.get_value()))
        )
        grid_mic.attach(self.spin_volume, 1, 0, 1, 1)
        grid_mic.attach(Gtk.Label(label="%"), 2, 0, 1, 1)

        # Noise Suppression
        self.check_noise = Gtk.CheckButton(label="🔇  WebRTC Noise Suppression (module-echo-cancel)")
        self.check_noise.set_active(self.temp_settings.get("noise_suppression", False))
        self.check_noise.connect(
            "toggled", lambda w: self._set_temp("noise_suppression", w.get_active())
        )
        grid_mic.attach(self.check_noise, 0, 1, 3, 1)

        # Mic Boost
        lbl_boost = Gtk.Label(label="ALSA Mic Boost:")
        lbl_boost.set_halign(Gtk.Align.START)
        grid_mic.attach(lbl_boost, 0, 2, 1, 1)

        self.spin_boost = Gtk.SpinButton.new_with_range(0, 100, 10)
        self.spin_boost.set_value(self.temp_settings.get("mic_boost", 0))
        self.spin_boost.connect(
            "value-changed", lambda w: self._set_temp("mic_boost", int(w.get_value()))
        )
        grid_mic.attach(self.spin_boost, 1, 2, 1, 1)
        grid_mic.attach(Gtk.Label(label="%"), 2, 2, 1, 1)

        # Auto-calibrate button
        btn_cal = Gtk.Button(label="📊 Auto-Calibrate Silence Threshold")
        btn_cal.connect("clicked", self._on_auto_calibrate)
        grid_mic.attach(btn_cal, 0, 3, 3, 1)

        self.lbl_cal_result = Gtk.Label(label="")
        self.lbl_cal_result.set_halign(Gtk.Align.START)
        grid_mic.attach(self.lbl_cal_result, 0, 4, 3, 1)

        # --- Spell Correction Toggle (Phase 3) ---
        frame_spell = Gtk.Frame(label="🖊️  Speech Processing")
        vbox.pack_start(frame_spell, False, False, 0)

        grid_spell = Gtk.Grid()
        grid_spell.set_column_spacing(10)
        grid_spell.set_row_spacing(6)
        grid_spell.set_margin_top(8)
        grid_spell.set_margin_bottom(8)
        grid_spell.set_margin_start(10)
        grid_spell.set_margin_end(10)
        frame_spell.add(grid_spell)

        self.check_spell = Gtk.CheckButton(
            label="✨  Spell Correction (SymSpellPy + ASR artifact rules)"
        )
        self.check_spell.set_active(self.temp_settings.get("spell_correction", True))
        self.check_spell.connect(
            "toggled", lambda w: self._set_temp("spell_correction", w.get_active())
        )
        grid_spell.attach(self.check_spell, 0, 0, 2, 1)

        self.check_voice_punct = Gtk.CheckButton(
            label=". , ?  Voice Punctuation (say 'period', 'comma', 'new line')"
        )
        self.check_voice_punct.set_active(self.temp_settings.get("voice_punctuation", True))
        self.check_voice_punct.connect(
            "toggled", lambda w: self._set_temp("voice_punctuation", w.get_active())
        )
        grid_spell.attach(self.check_voice_punct, 0, 1, 2, 1)

        # -- Actions --
        btn_logs = Gtk.Button(label="View Logs")
        btn_logs.connect("clicked", self._on_view_logs)
        vbox.pack_start(btn_logs, False, False, 0)

        self.is_testing = False
        self.test_stream = None
        self.pa = None
        
        # Trigger initial visibility state
        self._update_visibility()
        
        self.show_all()
        # Re-apply visibility filtering (show_all shows everything)
        self._update_visibility()

    def _set_temp(self, key, value):
        self.temp_settings[key] = value

    def _update_visibility(self):
        engine = self.combo_engine.get_active_text()
        if engine == "Vosk":
            self.lbl_vosk_path.show()
            self.file_chooser.show()
            self.lbl_whisper_size.hide()
            self.combo_whisper.hide()
            # Advanced frame is now shared
            self.frame_adv.show()
        else:
            self.lbl_vosk_path.hide()
            self.file_chooser.hide()
            self.lbl_whisper_size.show()
            self.combo_whisper.show()
            self.frame_adv.show()

    def _on_engine_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self._set_temp("speech_engine", text)
            self._update_visibility()

    def _on_whisper_size_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self._set_temp("whisper_model_size", text)

    def _on_device_changed(self, combo):
        idx = combo.get_active()
        if idx >= 0:
            source = self.sources[idx]
            self._set_temp("audio_device", source.name)

    def _on_model_set(self, widget):
        path = widget.get_filename()
        if path:
            self._set_temp("model_path", path)
            
    def _on_auto_calibrate(self, widget):
        """Run MicEnhancer auto-calibration in a background thread."""
        self.lbl_cal_result.set_text("Calibrating... stay quiet for 3 seconds.")
        widget.set_sensitive(False)

        def _run():
            try:
                from .mic_enhancer import MicEnhancer
                enh = MicEnhancer(self.settings)
                result = enh.auto_calibrate()
                recommended = result.get("recommended_threshold", 500)
                GLib.idle_add(
                    self.lbl_cal_result.set_text,
                    f"✅ Noise floor: {result.get('noise_floor_rms',0):.0f} RMS  "
                    f"→ Recommended threshold: {recommended}"
                )
                GLib.idle_add(self.spin_thresh.set_value, float(recommended))
                GLib.idle_add(self._set_temp, "silence_threshold", recommended)
            except Exception as e:
                GLib.idle_add(self.lbl_cal_result.set_text, f"❌ Calibration failed: {e}")
            finally:
                GLib.idle_add(widget.set_sensitive, True)

        threading.Thread(target=_run, daemon=True).start()

    def _on_view_logs(self, widget):
        import subprocess

        from .config import LOG_FILE
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
            return False  # Stop timer

        try:
            import numpy as np
            data = self.test_stream.read(1024, exception_on_overflow=False)
            self.recorded_frames.append(data)
            pcm = np.frombuffer(data, dtype=np.int16)
            rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
            self.level_bar.set_value(min(rms / 10000.0, 1.0))
        except Exception:
            pass

        return True

    def save_settings(self):
        changes = False
        reinit_engine = False
        
        # Check Audio Device changes specifically for PulseAudio logic
        new_device = self.temp_settings.get("audio_device")
        old_device = self.settings.get("audio_device")
        
        if new_device != old_device and new_device:
            try:
                from .pulseaudio_helper import set_default_source
                set_default_source(new_device)
            except ImportError:
                pass

        # Apply all settings
        for key, value in self.temp_settings.items():
            if self.settings.get(key) != value:
                self.settings.set(key, value)
                changes = True
                if key in ["speech_engine", "whisper_model_size", "model_path"]:
                    reinit_engine = True

        # Trigger callback if needed
        if changes and self.engine_change_callback:
            if reinit_engine:
                 self.engine_change_callback()


    def destroy(self):
        self._stop_test()
        super().destroy()


# End of SettingsDialog
