import logging
import os

logger = logging.getLogger(__name__)

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
import cairo  # noqa: E402  (for OSD waveform)
from gi.repository import AppIndicator3, GLib, Gtk, Gdk, Pango, PangoCairo  # noqa: E402

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
        self._last_activity = 0.0   # timestamp of last non-zero level or text
        self._auto_hide_ms = 3000   # hide after 3s of silence

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
        if text:
            import time
            self._last_activity = time.monotonic()
        GLib.idle_add(self._draw_area.queue_draw)

    def set_level(self, level: float):
        """level: 0.0 – 1.0"""
        import time
        self._level = max(0.0, min(1.0, level))
        if self._level > 0.04:          # mic is picking up audio
            self._last_activity = time.monotonic()
        GLib.idle_add(self._draw_area.queue_draw)
        # auto-hide after 3s of silence
        GLib.timeout_add(self._auto_hide_ms, self._check_auto_hide)

    def _check_auto_hide(self):
        import time
        idle_s = time.monotonic() - self._last_activity
        if idle_s >= (self._auto_hide_ms / 1000.0):
            GLib.idle_add(self.hide)
        return False  # one-shot

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

        # Settings reference for tray mode label
        from .settings import SettingsManager
        self._settings = SettingsManager()

        # P5: OSD overlay — hidden until listening starts
        self.osd = OSDOverlay()

        # AppIndicator3 — standard tray icon on modern GNOME/Ubuntu
        # (replaces deprecated Gtk.StatusIcon; credit: stiv-pro PR #2)
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            os.path.join(ASSETS_DIR, f"{ICON_IDLE}.svg"),
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("VoxInput")

        self.menu = self._build_menu()
        self.indicator.set_menu(self.menu)

    def _build_menu(self):
        menu = Gtk.Menu()

        # Mode indicator (non-clickable informational label)
        self._item_mode = Gtk.MenuItem(label=self._get_mode_label())
        self._item_mode.set_sensitive(False)
        menu.append(self._item_mode)

        menu.append(Gtk.SeparatorMenuItem())

        # Toggle Item
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

    def _get_mode_label(self, settings=None) -> str:
        """Return the current input mode for the tray indicator."""
        s = settings or self._settings
        if s and s.get("push_to_talk", False):
            key_str = s.get("ptt_key", "Key.ctrl_r")
            # Inline key formatting to avoid cross-class reference
            _DISPLAY = {
                "Key.ctrl_r": "Right Ctrl", "Key.ctrl_l": "Left Ctrl",
                "Key.alt_r": "Right Alt", "Key.alt_l": "Left Alt",
                "Key.shift_r": "Right Shift", "Key.shift_l": "Left Shift",
                "Key.scroll_lock": "Scroll Lock", "Key.pause": "Pause",
            }
            for i in range(1, 25):
                _DISPLAY[f"Key.f{i}"] = f"F{i}"
            key_name = _DISPLAY.get(key_str, key_str.replace("Key.", "").replace("_", " ").title())
            return f"Mode: Push-to-Talk ({key_name})"
        return "Mode: Toggle (Super+Shift+V)"

    def update_mode_label(self, settings=None):
        """Refresh the tray menu mode label after settings change."""
        if hasattr(self, '_item_mode'):
            try:
                self._item_mode.set_label(self._get_mode_label(settings))
            except Exception:
                pass

    def _on_toggle_menu(self, _):
        # Callback from menu item
        self.toggle_callback()
        
    def _on_settings(self, _):
        # Singleton: only one Settings window at a time
        if hasattr(self, '_settings_dialog') and self._settings_dialog is not None:
            self._settings_dialog.present()  # raise existing window
            return
        self._settings_dialog = SettingsDialog(self.engine_change_callback)
        self._settings_dialog._tray_app = self  # for mode label refresh
        self._settings_dialog.connect("destroy", lambda _: setattr(self, '_settings_dialog', None))
        self._settings_dialog.show()

    def _on_quit(self, _):
        self.quit_callback()

    def set_listening_state(self, is_listening):
        self.is_listening = is_listening
        if is_listening:
            self.indicator.set_icon_full(
                os.path.join(ASSETS_DIR, f"{ICON_ACTIVE}.svg"), "Listening")
            GLib.idle_add(self.item_toggle.set_label, "Stop Listening")
            GLib.idle_add(self.osd.show_all)   # P5: show OSD
        else:
            self.indicator.set_icon_full(
                os.path.join(ASSETS_DIR, f"{ICON_IDLE}.svg"), "Idle")
            GLib.idle_add(self.item_toggle.set_label, "Start Listening")
            GLib.idle_add(self.osd.hide)        # P5: hide OSD
            GLib.idle_add(self.osd.set_text, "")

    def update_osd(self, text: str, level: float = 0.0):
        """Called from main.py injection thread to update the OSD in real-time."""
        self.osd.set_text(text)
        self.osd.set_level(level)

    def run(self):
        Gtk.main()


# ─── CSS ───────────────────────────────────────────────────────────────────────

_SETTINGS_CSS = """
/* Base window */
window.settings-dialog,
window.settings-dialog > *,
window.settings-dialog box,
window.settings-dialog scrolledwindow,
window.settings-dialog viewport,
window.settings-dialog frame,
window.settings-dialog .tab-content {
    background-color: #1a1a2e;
    color: #c8d0e0;
}

/* Notebook tabs */
notebook { background-color: #1a1a2e; }
notebook header { background-color: #16213e; border-bottom: 2px solid #0f3460; }
notebook tab { padding: 10px 20px; color: #8892a4; font-weight: 600; font-size: 12px; }
notebook tab:checked { color: #e94560; border-bottom: 3px solid #e94560; background-color: #1a1a2e; }
notebook tab label { color: inherit; }
notebook stack { background-color: #1a1a2e; }

/* Labels */
label { color: #c8d0e0; }
.section-title { color: #e94560; font-weight: 700; font-size: 11px; letter-spacing: 1px; }
.hint { color: #5a6478; font-size: 10px; font-style: italic; }

/* Separators */
separator { background-color: #1e2a45; min-height: 1px; }

/* Entry / text fields */
entry {
    background-color: #0f253e;
    color: #e0e6f0;
    border: 1px solid #1a4a80;
    border-radius: 6px;
    padding: 5px 10px;
    caret-color: #e94560;
}
entry:focus { border-color: #e94560; box-shadow: 0 0 0 2px rgba(233,69,96,0.2); }

/* SpinButton - inner entry AND arrow buttons */
spinbutton {
    background-color: #0f253e;
    border: 1px solid #1a4a80;
    border-radius: 6px;
    color: #e0e6f0;
}
spinbutton entry,
spinbutton > entry,
spinbutton text {
    background-color: #0f253e;
    color: #e0e6f0;
    border: none;
    padding: 4px 6px;
}
spinbutton button,
spinbutton > button {
    background-color: #16213e;
    border: none;
    border-left: 1px solid #1a4a80;
    border-radius: 0;
    color: #e94560;
    padding: 2px 8px;
    min-width: 28px;
}
spinbutton button:hover { background-color: #0f3460; }
spinbutton button:first-child { border-left: none; border-right: 1px solid #1a4a80; border-radius: 6px 0 0 6px; }
spinbutton button:last-child { border-radius: 0 6px 6px 0; }

/* ComboBox */
combobox button,
combobox > button,
combobox button.combo {
    background-color: #0f253e;
    color: #e0e6f0;
    border: 1px solid #1a4a80;
    border-radius: 6px;
    padding: 5px 10px;
}
combobox button:hover { border-color: #e94560; background-color: #16213e; }
combobox arrow { color: #e94560; }
popover { background-color: #16213e; }
popover row { background-color: #16213e; color: #c8d0e0; }
popover row:hover { background-color: #0f3460; }

/* FileChooserButton */
filechooserbutton,
filechooserbutton button {
    background-color: #0f253e;
    color: #e0e6f0;
    border: 1px solid #1a4a80;
    border-radius: 6px;
    padding: 5px 10px;
}
filechooserbutton button:hover { border-color: #e94560; background-color: #16213e; }

/* Checkbutton */
checkbutton { color: #c8d0e0; }
checkbutton check {
    background-color: #0f253e;
    border: 1.5px solid #1a4a80;
    border-radius: 4px;
    min-width: 16px;
    min-height: 16px;
}
checkbutton:checked check { background-color: #e94560; border-color: #e94560; }

/* Buttons */
button, button.text-button {
    background-color: #0f3460;
    background-image: none;
    color: #e0e6f0;
    border: 1px solid #1a4a80;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    box-shadow: none;
    transition: all 150ms ease;
}
button:hover { background-color: #1a4a80; border-color: #e94560; color: #ffffff; }
button:active { background-color: #0a2040; }

button.action-btn, button.action-btn.text-button {
    background: linear-gradient(135deg, #e94560, #b83050);
    background-image: linear-gradient(135deg, #e94560, #b83050);
    border: none;
    color: #ffffff;
    font-size: 13px;
    padding: 10px 28px;
    border-radius: 10px;
}
button.action-btn:hover { background: linear-gradient(135deg, #ff5577, #e94560); background-image: linear-gradient(135deg, #ff5577, #e94560); }

button.cancel-btn, button.cancel-btn.text-button {
    background-color: transparent;
    background-image: none;
    border: 1px solid #3a4458;
    color: #8892a4;
}
button.cancel-btn:hover { border-color: #e94560; color: #e94560; background-color: rgba(233,69,96,0.08); }

/* Level bar */
levelbar trough { background-color: #0f253e; border: none; border-radius: 4px; }
levelbar block.filled { background: linear-gradient(90deg, #00d4cc, #e94560); border-radius: 3px; }

/* Scrollbar */
scrollbar trough { background-color: #16213e; }
scrollbar slider { background-color: #1a4a80; border-radius: 4px; min-width: 6px; }
scrollbar slider:hover { background-color: #e94560; }
"""





def _apply_settings_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(_SETTINGS_CSS.encode('utf-8'))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def _row(label_text, widget, hint=None):
    """Build a label+widget row for a grid attachment."""
    lbl = Gtk.Label(label=label_text)
    lbl.set_halign(Gtk.Align.START)
    lbl.set_valign(Gtk.Align.CENTER)
    if hint:
        h = Gtk.Label()
        h.set_markup(f'<span size="small"><i>{hint}</i></span>')
        h.get_style_context().add_class("hint")
        h.set_halign(Gtk.Align.START)
        h.set_line_wrap(True)
        return lbl, widget, h
    return lbl, widget


def _section_label(text):
    lbl = Gtk.Label()
    lbl.set_markup(f'<span weight="bold" size="small">{text.upper()}</span>')
    lbl.get_style_context().add_class("section-title")
    lbl.set_halign(Gtk.Align.START)
    lbl.set_margin_top(8)
    lbl.set_margin_bottom(4)
    return lbl


class SettingsDialog(Gtk.Window):
    """
    VoxInput Settings — compact tabbed window.
    Always fits on screen; Save/Cancel always reachable.

    Tabs:
      🎤 Audio   — device, mic test, enhancement
      🧠 Engine  — Vosk/Whisper, silence tuning, speed mode
      ✏️ Processing — spell correction, punctuation, logs
    """

    def __init__(self, engine_change_callback=None):
        super().__init__(title="VoxInput Settings")
        self.engine_change_callback = engine_change_callback
        self.get_style_context().add_class("settings-dialog")

        _apply_settings_css()

        from .settings import SettingsManager
        self.settings = SettingsManager()
        self.temp_settings = self.settings.settings.copy()

        self.set_default_size(672, 820)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(True)
        self.connect("delete-event", self._on_delete)

        self.is_testing = False
        self.test_stream = None
        self.pa = None

        # ── Root layout: notebook + button bar ─────────────────
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.notebook.set_show_border(False)
        root.pack_start(self.notebook, True, True, 0)

        # ── Tabs ────────────────────────────────────────────────
        self.notebook.append_page(self._build_audio_tab(),      Gtk.Label(label="🎤  Audio"))
        self.notebook.append_page(self._build_engine_tab(),     Gtk.Label(label="🧠  Engine"))
        self.notebook.append_page(self._build_processing_tab(), Gtk.Label(label="✏️  Processing"))
        self.notebook.append_page(self._build_words_tab(),      Gtk.Label(label="📖  Words"))

        # ── Button bar ──────────────────────────────────────────
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(sep, False, False, 0)

        btn_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_bar.set_margin_top(10)
        btn_bar.set_margin_bottom(12)
        btn_bar.set_margin_start(16)
        btn_bar.set_margin_end(16)
        root.pack_start(btn_bar, False, False, 0)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.get_style_context().add_class("cancel-btn")
        btn_cancel.connect("clicked", lambda _: self._close(save=False))

        btn_save = Gtk.Button(label="  Save Settings  ")
        btn_save.get_style_context().add_class("action-btn")
        btn_save.connect("clicked", lambda _: self._close(save=True))

        btn_bar.pack_end(btn_save, False, False, 0)
        btn_bar.pack_end(btn_cancel, False, False, 0)

        self._update_engine_visibility()
        self.show_all()
        self._update_engine_visibility()

    # ── Tab builders ────────────────────────────────────────────────────────────

    def _build_audio_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.get_style_context().add_class("tab-content")
        scroll.add(vbox)

        # ── Device ─────────────────────────────────────────────
        vbox.pack_start(_section_label("Input Device"), False, False, 0)

        dev_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_dev = Gtk.Label(label="Microphone:")
        lbl_dev.set_halign(Gtk.Align.START)
        lbl_dev.set_width_chars(16)
        dev_row.pack_start(lbl_dev, False, False, 0)

        self.combo = Gtk.ComboBoxText()
        dev_row.pack_start(self.combo, True, True, 0)
        vbox.pack_start(dev_row, False, False, 4)

        try:
            from .pulseaudio_helper import filter_input_sources, get_default_source, get_pulseaudio_sources
            self.sources = filter_input_sources(get_pulseaudio_sources())
            saved_device = self.temp_settings.get("audio_device")
            current_default = get_default_source()
            target_device = saved_device if saved_device else current_default
            active_index = -1
            for i, source in enumerate(self.sources):
                self.combo.append_text(f"{source.description}")
                if source.name == target_device:
                    active_index = i
            if active_index != -1:
                self.combo.set_active(active_index)
            elif self.sources:
                self.combo.set_active(0)
            self.combo.connect("changed", self._on_device_changed)
        except ImportError:
            self.combo.append_text("pulseaudio_helper not found")
            self.combo.set_sensitive(False)
            self.sources = []

        # ── Audio Test Bed ──────────────────────────────────────
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)
        vbox.pack_start(_section_label("🎙️  Audio Test Bed"), False, False, 0)

        test_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_level = Gtk.Label(label="Input level:")
        lbl_level.set_halign(Gtk.Align.START)
        lbl_level.set_width_chars(16)
        test_row.pack_start(lbl_level, False, False, 0)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_size_request(200, 12)
        test_row.pack_start(self.level_bar, True, True, 0)

        self.btn_test = Gtk.Button(label="▶  Record")
        self.btn_test.connect("clicked", self._on_toggle_test)
        test_row.pack_start(self.btn_test, False, False, 0)
        vbox.pack_start(test_row, False, False, 4)

        # ── Volume Controls ─────────────────────────────────────
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)
        vbox.pack_start(_section_label("🔊  Volume Controls"), False, False, 0)

        # Mic input volume (0–100%)
        mic_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_mic = Gtk.Label(label="🎤 Mic Input:")
        lbl_mic.set_halign(Gtk.Align.START)
        lbl_mic.set_width_chars(16)
        mic_row.pack_start(lbl_mic, False, False, 0)
        self.scale_mic = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale_mic.set_value(self.temp_settings.get("mic_volume", 100))
        self.scale_mic.set_draw_value(True)
        self.scale_mic.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_mic.connect("value-changed", self._on_mic_volume_changed)
        mic_row.pack_start(self.scale_mic, True, True, 0)
        mic_row.pack_start(Gtk.Label(label="%"), False, False, 0)
        vbox.pack_start(mic_row, False, False, 4)

        # Speaker output volume (0–100%)
        spk_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_spk = Gtk.Label(label="🔈 Speaker:")
        lbl_spk.set_halign(Gtk.Align.START)
        lbl_spk.set_width_chars(16)
        spk_row.pack_start(lbl_spk, False, False, 0)
        self.scale_spk = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        # Read current system speaker volume
        try:
            from .mic_enhancer import MicEnhancer
            _tmp = MicEnhancer(self.settings)
            self.scale_spk.set_value(_tmp.get_output_volume())
        except Exception:
            self.scale_spk.set_value(50)
        self.scale_spk.set_draw_value(True)
        self.scale_spk.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_spk.connect("value-changed", self._on_spk_volume_changed)
        spk_row.pack_start(self.scale_spk, True, True, 0)
        spk_row.pack_start(Gtk.Label(label="%"), False, False, 0)
        vbox.pack_start(spk_row, False, False, 4)

        # ── Enhancement ─────────────────────────────────────────
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)
        vbox.pack_start(_section_label("🛠️  Microphone Enhancement"), False, False, 0)

        self.check_noise = Gtk.CheckButton(label="🔇  WebRTC Noise Suppression")
        self.check_noise.set_active(self.temp_settings.get("noise_suppression", False))
        self.check_noise.connect("toggled", self._on_webrtc_toggled)
        vbox.pack_start(self.check_noise, False, False, 2)

        # Sub-feature checkboxes (indented under main toggle)
        webrtc_sub_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        webrtc_sub_box.set_margin_start(24)

        self.check_hpf = Gtk.CheckButton(label="High-Pass Filter (cuts rumble < 80Hz)")
        self.check_hpf.set_active(self.temp_settings.get("webrtc_high_pass_filter", True))
        self.check_hpf.connect("toggled", lambda w: self._on_webrtc_sub_toggled("webrtc_high_pass_filter", w))
        webrtc_sub_box.pack_start(self.check_hpf, False, False, 0)

        self.check_vad = Gtk.CheckButton(label="Voice Activity Detection")
        self.check_vad.set_active(self.temp_settings.get("webrtc_voice_detection", True))
        self.check_vad.connect("toggled", lambda w: self._on_webrtc_sub_toggled("webrtc_voice_detection", w))
        webrtc_sub_box.pack_start(self.check_vad, False, False, 0)

        self.check_dgc = Gtk.CheckButton(label="Digital Gain Control (software normalization)")
        self.check_dgc.set_active(self.temp_settings.get("webrtc_digital_gain", True))
        self.check_dgc.connect("toggled", lambda w: self._on_webrtc_sub_toggled("webrtc_digital_gain", w))
        webrtc_sub_box.pack_start(self.check_dgc, False, False, 0)

        self.check_agc = Gtk.CheckButton(label="Analog Gain Control (hardware auto-adjust)")
        self.check_agc.set_active(self.temp_settings.get("webrtc_analog_gain", False))
        self.check_agc.connect("toggled", lambda w: self._on_webrtc_sub_toggled("webrtc_analog_gain", w))
        webrtc_sub_box.pack_start(self.check_agc, False, False, 0)

        # Sub-features: always visible, greyed out when parent is off
        self._webrtc_sub_box = webrtc_sub_box
        noise_on = self.temp_settings.get("noise_suppression", False)
        webrtc_sub_box.set_sensitive(noise_on)
        if not noise_on:
            self.check_hpf.set_active(False)
            self.check_vad.set_active(False)
            self.check_dgc.set_active(False)
            self.check_agc.set_active(False)
        vbox.pack_start(webrtc_sub_box, False, False, 2)

        # ── RNNoise AI Denoiser ─────────────────────────────────
        from .mic_enhancer import MicEnhancer
        _enhancer_probe = MicEnhancer(self.settings)
        rnnoise_available = _enhancer_probe.is_rnnoise_available()

        if rnnoise_available:
            rnnoise_label = "🧠  RNNoise AI Denoiser (neural network — better quality, more CPU)"
        else:
            rnnoise_label = "🧠  RNNoise AI Denoiser (not installed)"

        self.check_rnnoise = Gtk.CheckButton(label=rnnoise_label)
        self.check_rnnoise.set_active(self.temp_settings.get("rnnoise_enabled", False))
        self.check_rnnoise.set_sensitive(rnnoise_available)
        self.check_rnnoise.connect("toggled", self._on_rnnoise_toggled)
        vbox.pack_start(self.check_rnnoise, False, False, 2)

        # Mutual exclusion hints
        rnnoise_hint = Gtk.Label(label="")
        rnnoise_hint.set_halign(Gtk.Align.START)
        rnnoise_hint.set_margin_start(24)
        rnnoise_hint.get_style_context().add_class("hint")
        if not rnnoise_available:
            rnnoise_hint.set_text("Install: sudo apt install ladspa-sdk && download librnnoise_ladspa.so")
        else:
            rnnoise_hint.set_text("⚡ Alternative to WebRTC — can't run both at once")
        self._rnnoise_hint = rnnoise_hint
        vbox.pack_start(rnnoise_hint, False, False, 0)

        # ── EasyEffects Integration ─────────────────────────────
        ee_installed = MicEnhancer.is_easyeffects_installed()
        ee_running = MicEnhancer.is_easyeffects_running() if ee_installed else False

        if not ee_installed:
            ee_label = "🎛️  Install EasyEffects (full audio EQ/compressor)"
        elif ee_running:
            ee_label = "🎛️  EasyEffects — Running ✅"
        else:
            ee_label = "🎛️  Launch EasyEffects (EQ, compressor, gate, de-esser)"

        self.btn_easyeffects = Gtk.Button(label=ee_label)
        self.btn_easyeffects.connect("clicked", self._on_easyeffects_clicked)
        vbox.pack_start(self.btn_easyeffects, False, False, 4)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)

        boost_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_boost = Gtk.Label(label="ALSA Mic Boost:")
        lbl_boost.set_halign(Gtk.Align.START)
        lbl_boost.set_width_chars(16)
        boost_row.pack_start(lbl_boost, False, False, 0)
        self.spin_boost = Gtk.SpinButton.new_with_range(0, 100, 10)
        self.spin_boost.set_value(self.temp_settings.get("mic_boost", 0))
        self.spin_boost.connect("value-changed", lambda w: self._set_temp("mic_boost", int(w.get_value())))
        boost_row.pack_start(self.spin_boost, False, False, 0)
        boost_row.pack_start(Gtk.Label(label="%"), False, False, 0)
        vbox.pack_start(boost_row, False, False, 4)

        btn_cal = Gtk.Button(label="📊  Auto-Calibrate Silence Threshold")
        btn_cal.connect("clicked", self._on_auto_calibrate)
        vbox.pack_start(btn_cal, False, False, 6)

        self.lbl_cal_result = Gtk.Label(label="")
        self.lbl_cal_result.set_halign(Gtk.Align.START)
        self.lbl_cal_result.get_style_context().add_class("hint")
        # Show existing calibration if saved
        saved_thresh = self.temp_settings.get("silence_threshold", 500)
        if saved_thresh != 500:
            self.lbl_cal_result.set_text(f"✅ Calibrated — threshold: {saved_thresh}")
        else:
            self.lbl_cal_result.set_text("⚠️ Not calibrated — recommended for best results")
        vbox.pack_start(self.lbl_cal_result, False, False, 0)

        return scroll

    def _build_engine_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.get_style_context().add_class("tab-content")
        scroll.add(vbox)

        # ── Engine type ─────────────────────────────────────────
        vbox.pack_start(_section_label("Speech Engine"), False, False, 0)

        eng_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_eng = Gtk.Label(label="Engine:")
        lbl_eng.set_halign(Gtk.Align.START)
        lbl_eng.set_width_chars(18)
        eng_row.pack_start(lbl_eng, False, False, 0)
        self.combo_engine = Gtk.ComboBoxText()
        self.combo_engine.append_text("Vosk")
        self.combo_engine.append_text("Whisper")
        saved_engine = self.temp_settings.get("speech_engine", "Vosk")
        self.combo_engine.set_active(1 if saved_engine == "Whisper" else 0)
        self.combo_engine.connect("changed", self._on_engine_changed)
        eng_row.pack_start(self.combo_engine, False, False, 0)
        vbox.pack_start(eng_row, False, False, 4)

        # Vosk model path (shown for Vosk)
        self.vosk_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_vosk_path = Gtk.Label(label="Vosk Model:")
        self.lbl_vosk_path.set_halign(Gtk.Align.START)
        self.lbl_vosk_path.set_width_chars(18)
        self.vosk_row.pack_start(self.lbl_vosk_path, False, False, 0)
        self.combo_vosk_model = Gtk.ComboBoxText()
        model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
        models = []
        if os.path.exists(model_dir):
            models = [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d))]
            
        saved_model_path = self.temp_settings.get("model_path", "")
        saved_model_name = os.path.basename(saved_model_path) if saved_model_path else "default_model"
        
        active_idx = 0
        for i, m in enumerate(sorted(models)):
            self.combo_vosk_model.append_text(m)
            if m == saved_model_name:
                active_idx = i
                
        self.combo_vosk_model.connect("changed", self._on_vosk_model_changed)
        
        if models:
            self.combo_vosk_model.set_active(active_idx)

        self.vosk_row.pack_start(self.combo_vosk_model, True, True, 0)
        vbox.pack_start(self.vosk_row, False, False, 4)

        # Whisper model size (shown for Whisper)
        self.whisper_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_whisper_size = Gtk.Label(label="Whisper Model:")
        self.lbl_whisper_size.set_halign(Gtk.Align.START)
        self.lbl_whisper_size.set_width_chars(18)
        self.whisper_row.pack_start(self.lbl_whisper_size, False, False, 0)
        self.combo_whisper = Gtk.ComboBoxText()
        WHISPER_SIZES = ["tiny", "base", "small", "medium", "large", "large-v3-turbo", "distil-large-v3"]
        for sz in WHISPER_SIZES:
            self.combo_whisper.append_text(sz)
        saved_size = self.temp_settings.get("whisper_model_size", "base")
        try:
            self.combo_whisper.set_active(WHISPER_SIZES.index(saved_size))
        except ValueError:
            self.combo_whisper.set_active(1)
        self.combo_whisper.connect("changed", self._on_whisper_size_changed)
        self.whisper_row.pack_start(self.combo_whisper, False, False, 0)
        vbox.pack_start(self.whisper_row, False, False, 4)

        # ── Tuning ──────────────────────────────────────────────
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)
        vbox.pack_start(_section_label("Silence Tuning"), False, False, 0)

        def _spin_row(label, low, high, step, key, default, fmt=None, hint=None):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lbl = Gtk.Label(label=label)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_width_chars(22)
            row.pack_start(lbl, False, False, 0)
            spin = Gtk.SpinButton.new_with_range(low, high, step)
            spin.set_value(self.temp_settings.get(key, default))
            spin.connect("value-changed", lambda w: self._set_temp(key, (round(w.get_value(), 2) if step < 1 else int(w.get_value()))))
            row.pack_start(spin, False, False, 0)
            if fmt:
                row.pack_start(Gtk.Label(label=fmt), False, False, 0)
            vbox.pack_start(row, False, False, 4)
            if hint:
                hl = Gtk.Label()
                hl.set_markup(f'<span size="small"><i>{hint}</i></span>')
                hl.get_style_context().add_class("hint")
                hl.set_halign(Gtk.Align.START)
                hl.set_line_wrap(True)
                vbox.pack_start(hl, False, False, 2)
            return spin

        self.spin_silence = _spin_row(
            "Pause after speech:", 0.1, 5.0, 0.1, "silence_duration", 0.6, "s",
            "Lower = snappier. Higher = allows longer pauses."
        )
        self.spin_thresh = _spin_row(
            "Noise threshold:", 0, 5000, 100, "silence_threshold", 500, "RMS",
            "Raise if background noise triggers typing."
        )
        self.spin_lag = _spin_row(
            "Stability lag:", 0, 10, 1, "stability_lag", 2, "words",
            "Words held back to prevent flicker. 0 = instant."
        )

        # ── Speed mode ──────────────────────────────────────────
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 6)
        self.check_fast_mode = Gtk.CheckButton(label="⚡  Speed Mode (LAG=0 — instant output, may reduce accuracy)")
        self.check_fast_mode.set_active(self.temp_settings.get("fast_mode", False))
        self.check_fast_mode.connect("toggled", lambda w: self._set_temp("fast_mode", w.get_active()))
        vbox.pack_start(self.check_fast_mode, False, False, 6)

        return scroll

    def _build_processing_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.get_style_context().add_class("tab-content")
        vbox.pack_start(inner, True, True, 0)
        scroll.add(vbox)

        inner.pack_start(_section_label("✏️  Speech Processing"), False, False, 0)

        self.check_spell = Gtk.CheckButton(label="✨  Spell Correction (SymSpellPy + ASR artifact rules)")
        self.check_spell.set_active(self.temp_settings.get("spell_correction", True))
        self.check_spell.connect("toggled", lambda w: self._set_temp("spell_correction", w.get_active()))
        inner.pack_start(self.check_spell, False, False, 4)

        self.check_voice_punct = Gtk.CheckButton(label=". , ?  Voice Punctuation (say 'period', 'comma', 'new line')")
        self.check_voice_punct.set_active(self.temp_settings.get("voice_punctuation", True))
        self.check_voice_punct.connect("toggled", lambda w: self._set_temp("voice_punctuation", w.get_active()))
        inner.pack_start(self.check_voice_punct, False, False, 4)

        self.check_autocap = Gtk.CheckButton(label="Aa  Auto-Capitalization (capitalize after sentence-end)")
        self.check_autocap.set_active(self.temp_settings.get("auto_capitalization", True))
        self.check_autocap.connect("toggled", lambda w: self._set_temp("auto_capitalization", w.get_active()))
        inner.pack_start(self.check_autocap, False, False, 4)

        self.check_numbers = Gtk.CheckButton(label="🔢  Number Conversion ('twenty one' → 21)")
        self.check_numbers.set_active(self.temp_settings.get("number_conversion", True))
        self.check_numbers.connect("toggled", lambda w: self._set_temp("number_conversion", w.get_active()))
        inner.pack_start(self.check_numbers, False, False, 4)

        self.check_homophones = Gtk.CheckButton(label="🔄  Homophone Fixer (their/there/they're)")
        self.check_homophones.set_active(self.temp_settings.get("homophones", True))
        self.check_homophones.connect("toggled", lambda w: self._set_temp("homophones", w.get_active()))
        inner.pack_start(self.check_homophones, False, False, 4)

        self.check_confidence = Gtk.CheckButton(label="🎯  Confidence Filter (drop low-confidence ASR words)")
        self.check_confidence.set_active(self.temp_settings.get("confidence_filter", True))
        self.check_confidence.connect("toggled", lambda w: self._set_temp("confidence_filter", w.get_active()))
        inner.pack_start(self.check_confidence, False, False, 4)

        inner.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 8)
        inner.pack_start(_section_label("🎙️  Input Mode"), False, False, 0)

        # Radio buttons: Toggle vs Push-to-Talk
        ptt_enabled = self.temp_settings.get("push_to_talk", False)
        self.radio_toggle = Gtk.RadioButton.new_with_label_from_widget(
            None, "🔄  Toggle Mode (Super+Shift+V to start/stop)"
        )
        self.radio_ptt = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_toggle, "🎙️  Push-to-Talk (hold key to dictate)"
        )
        if ptt_enabled:
            self.radio_ptt.set_active(True)
        else:
            self.radio_toggle.set_active(True)
        self.radio_toggle.connect("toggled", self._on_mode_radio_toggled)
        inner.pack_start(self.radio_toggle, False, False, 4)
        inner.pack_start(self.radio_ptt, False, False, 4)

        # PTT options box (visible only when PTT is selected)
        self._ptt_options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._ptt_options_box.set_margin_start(24)

        # Key selector row
        key_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        key_label = Gtk.Label(label="PTT Key:")
        key_label.set_halign(Gtk.Align.START)
        key_row.pack_start(key_label, False, False, 0)

        current_key = self.temp_settings.get("ptt_key", "Key.ctrl_r")
        self._ptt_key_label = Gtk.Label(label=self._format_key_name(current_key))
        self._ptt_key_label.set_width_chars(16)
        self._ptt_key_label.get_style_context().add_class("dim-label")
        key_row.pack_start(self._ptt_key_label, False, False, 0)

        self._ptt_record_btn = Gtk.Button(label="Record Key")
        self._ptt_record_btn.connect("clicked", self._on_record_ptt_key)
        key_row.pack_start(self._ptt_record_btn, False, False, 0)

        self._ptt_options_box.pack_start(key_row, False, False, 0)

        # Audio feedback toggle
        self.check_ptt_beep = Gtk.CheckButton(label="🔊  Audio feedback (beep on press/release)")
        self.check_ptt_beep.set_active(self.temp_settings.get("ptt_audio_feedback", True))
        self.check_ptt_beep.connect("toggled", lambda w: self._set_temp("ptt_audio_feedback", w.get_active()))
        self._ptt_options_box.pack_start(self.check_ptt_beep, False, False, 0)

        # Hint
        ptt_hint = Gtk.Label()
        ptt_hint.set_markup(
            '<span size="small"><i>Hold key to listen. On release, full-context '
            'grammar correction runs before injection.</i></span>'
        )
        ptt_hint.get_style_context().add_class("hint")
        ptt_hint.set_halign(Gtk.Align.START)
        ptt_hint.set_line_wrap(True)
        self._ptt_options_box.pack_start(ptt_hint, False, False, 0)

        inner.pack_start(self._ptt_options_box, False, False, 4)
        # Show/hide PTT options based on current selection
        self._ptt_options_box.set_visible(ptt_enabled)

        inner.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 8)
        inner.pack_start(_section_label("📋  Diagnostics"), False, False, 0)

        # Log level selector
        log_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        log_label = Gtk.Label(label="Log Level:")
        log_label.set_halign(Gtk.Align.START)
        log_row.pack_start(log_label, False, False, 0)

        from .logger import LOG_LEVELS
        self.combo_log_level = Gtk.ComboBoxText()
        current_level = self.temp_settings.get("log_level", "TRACE")
        for i, lvl in enumerate(LOG_LEVELS):
            self.combo_log_level.append_text(lvl)
            if lvl == current_level:
                self.combo_log_level.set_active(i)
        if self.combo_log_level.get_active() < 0:
            self.combo_log_level.set_active(0)  # fallback to TRACE
        self.combo_log_level.connect("changed", lambda w: self._set_temp("log_level", w.get_active_text()))
        log_row.pack_start(self.combo_log_level, False, False, 0)

        log_hint = Gtk.Label()
        log_hint.set_markup(
            '<span size="small"><i>TRACE = everything, ERROR = errors only</i></span>'
        )
        log_hint.get_style_context().add_class("hint")
        log_row.pack_start(log_hint, False, False, 8)

        inner.pack_start(log_row, False, False, 4)

        return scroll

    def _build_words_tab(self):
        """Protected words list — words that are never spell-corrected."""
        # Load word_db lazily (may not be ready during init; falls back gracefully)
        self._word_db = None
        try:
            import os
            from .word_db import WordDatabase
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "data", "custom_words.db"
            )
            self._word_db = WordDatabase(db_path)
        except Exception:
            pass

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class("tab-content")
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(16)
        outer.set_margin_end(16)

        outer.pack_start(_section_label("📖  Protected Words"), False, False, 0)

        hint = Gtk.Label(label="Words listed here are never spell-corrected. "
                               "Useful for names, brands, tech terms.")
        hint.set_line_wrap(True)
        hint.set_xalign(0)
        hint.get_style_context().add_class("hint")
        hint.set_margin_bottom(8)
        outer.pack_start(hint, False, False, 0)

        # ── Search bar ────────────────────────────────────────────
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_search = Gtk.Label(label="🔍")
        self._words_search = Gtk.Entry()
        self._words_search.set_placeholder_text("Filter words / categories…")
        self._words_search.connect("changed", self._on_words_filter_changed)
        search_box.pack_start(lbl_search, False, False, 0)
        search_box.pack_start(self._words_search, True, True, 0)
        outer.pack_start(search_box, False, False, 4)

        # ── TreeView ──────────────────────────────────────────────
        # Columns: word, category, added-date
        self._words_store = Gtk.ListStore(int, str, str, str)  # id, word, cat, date
        self._words_view  = Gtk.TreeView(model=self._words_store)
        self._words_view.set_headers_visible(True)
        self._words_view.set_activate_on_single_click(False)
        self._words_view.get_style_context().add_class("words-tree")

        for i, (title, expand) in enumerate([("Word", True), ("Category", False), ("Added", False)]):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i + 1)
            col.set_expand(expand)
            col.set_sort_column_id(i + 1)
            self._words_view.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(220)
        scroll.add(self._words_view)
        outer.pack_start(scroll, True, True, 4)

        # ── Word count label ──────────────────────────────────────
        self._words_count_label = Gtk.Label(label="")
        self._words_count_label.set_xalign(0)
        self._words_count_label.get_style_context().add_class("hint")
        outer.pack_start(self._words_count_label, False, False, 0)

        # ── Add row ───────────────────────────────────────────────
        outer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 8)
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._words_entry = Gtk.Entry()
        self._words_entry.set_placeholder_text("New word…")
        self._words_entry.connect("activate", self._on_word_add)

        # Category dropdown
        cat_store = Gtk.ListStore(str)
        for c in ["custom", "tech", "ai", "linux", "dev", "brand", "org",
                  "name", "place", "sports", "culture", "agile", "project", "future"]:
            cat_store.append([c])
        self._words_cat_combo = Gtk.ComboBox.new_with_model(cat_store)
        renderer = Gtk.CellRendererText()
        self._words_cat_combo.pack_start(renderer, True)
        self._words_cat_combo.add_attribute(renderer, "text", 0)
        self._words_cat_combo.set_active(0)

        btn_add = Gtk.Button(label="➕ Add")
        btn_add.get_style_context().add_class("action-btn")
        btn_add.connect("clicked", self._on_word_add)

        btn_remove = Gtk.Button(label="🗑️ Remove")
        btn_remove.get_style_context().add_class("cancel-btn")
        btn_remove.connect("clicked", self._on_word_remove)

        add_box.pack_start(self._words_entry,     True,  True,  0)
        add_box.pack_start(self._words_cat_combo, False, False, 0)
        add_box.pack_start(btn_add,               False, False, 0)
        add_box.pack_start(btn_remove,            False, False, 0)
        outer.pack_start(add_box, False, False, 0)

        self._refresh_words_list()
        return outer

    def _refresh_words_list(self, filter_text=""):
        """Reload the TreeView from the database."""
        self._words_store.clear()
        if self._word_db is None:
            return
        import datetime
        rows = self._word_db.get_all(filter_text)
        for row_id, word, cat, added_at in rows:
            ts = datetime.datetime.fromtimestamp(added_at).strftime("%Y-%m-%d") if added_at else ""
            self._words_store.append([row_id, word, cat, ts])
        total = self._word_db.count()
        visible = len(rows)
        if filter_text:
            self._words_count_label.set_text(f"{visible} shown / {total} total protected words")
        else:
            self._words_count_label.set_text(f"{total} protected words")

    def _on_words_filter_changed(self, entry):
        self._refresh_words_list(entry.get_text())

    def _on_word_add(self, _widget):
        word = self._words_entry.get_text().strip()
        if not word or self._word_db is None:
            return
        # Get selected category
        it = self._words_cat_combo.get_active_iter()
        cat = "custom"
        if it is not None:
            cat = self._words_cat_combo.get_model()[it][0]
        added = self._word_db.add_word(word, cat)
        if added:
            self._words_entry.set_text("")
            self._refresh_words_list(self._words_search.get_text())
        else:
            # Word already exists — flash entry red briefly
            self._words_entry.get_style_context().add_class("entry-error")
            GLib.timeout_add(800, lambda: (
                self._words_entry.get_style_context().remove_class("entry-error"), False
            ))

    def _on_word_remove(self, _widget):
        if self._word_db is None:
            return
        selection = self._words_view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return
        word = model[treeiter][1]
        self._word_db.remove_word(word)
        self._refresh_words_list(self._words_search.get_text())


    def _set_temp(self, key, value):
        self.temp_settings[key] = value

    # ── Input Mode handlers ──────────────────────────────────────

    def _on_mode_radio_toggled(self, radio):
        """Handle Toggle/PTT radio button change."""
        if not radio.get_active():
            return  # only respond to the newly activated radio
        ptt_on = self.radio_ptt.get_active()
        self._set_temp("push_to_talk", ptt_on)
        self._ptt_options_box.set_visible(ptt_on)

    def _on_record_ptt_key(self, btn):
        """Start listening for a key press to set as the PTT key."""
        btn.set_label("Press any key…")
        btn.set_sensitive(False)
        # Connect to the dialog's key-press-event (captures any key)
        self._ptt_key_handler_id = self.connect("key-press-event", self._on_ptt_key_captured)

    def _on_ptt_key_captured(self, widget, event):
        """Capture the pressed key and save it as the PTT key."""
        from pynput.keyboard import Key

        # Map GDK keyval to pynput key string
        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)

        # Map common GDK key names to pynput format
        _GDK_TO_PYNPUT = {
            "Control_R": "Key.ctrl_r", "Control_L": "Key.ctrl_l",
            "Alt_R": "Key.alt_r", "Alt_L": "Key.alt_l",
            "Shift_R": "Key.shift_r", "Shift_L": "Key.shift_l",
            "Super_R": "Key.cmd_r", "Super_L": "Key.cmd",
            "Scroll_Lock": "Key.scroll_lock", "Pause": "Key.pause",
            "Caps_Lock": "Key.caps_lock", "Num_Lock": "Key.num_lock",
            "Insert": "Key.insert", "Delete": "Key.delete",
            "Home": "Key.home", "End": "Key.end",
            "Page_Up": "Key.page_up", "Page_Down": "Key.page_down",
            "Menu": "Key.menu", "Print": "Key.print_screen",
        }
        # F-keys
        for i in range(1, 25):
            _GDK_TO_PYNPUT[f"F{i}"] = f"Key.f{i}"

        pynput_key = _GDK_TO_PYNPUT.get(keyname)
        if not pynput_key:
            # For printable chars, pynput uses the char directly wrapped in quotes
            pynput_key = f"'{keyname}'" if len(keyname) == 1 else f"Key.{keyname.lower()}"

        # Save to temp settings
        self._set_temp("ptt_key", pynput_key)
        self._ptt_key_label.set_text(self._format_key_name(pynput_key))
        self._ptt_record_btn.set_label("Record Key")
        self._ptt_record_btn.set_sensitive(True)

        # Disconnect the key capture handler
        if hasattr(self, '_ptt_key_handler_id'):
            self.disconnect(self._ptt_key_handler_id)

        return True  # consume the key event

    @staticmethod
    def _format_key_name(pynput_str: str) -> str:
        """Convert pynput key string to human-readable label."""
        _DISPLAY = {
            "Key.ctrl_r": "Right Ctrl", "Key.ctrl_l": "Left Ctrl",
            "Key.alt_r": "Right Alt", "Key.alt_l": "Left Alt",
            "Key.shift_r": "Right Shift", "Key.shift_l": "Left Shift",
            "Key.cmd": "Super", "Key.cmd_r": "Right Super",
            "Key.scroll_lock": "Scroll Lock", "Key.pause": "Pause",
            "Key.caps_lock": "Caps Lock", "Key.num_lock": "Num Lock",
            "Key.insert": "Insert", "Key.delete": "Delete",
            "Key.home": "Home", "Key.end": "End",
            "Key.page_up": "Page Up", "Key.page_down": "Page Down",
            "Key.menu": "Menu", "Key.print_screen": "Print Screen",
        }
        # F-keys
        for i in range(1, 25):
            _DISPLAY[f"Key.f{i}"] = f"F{i}"

        return _DISPLAY.get(pynput_str, pynput_str.replace("Key.", "").replace("_", " ").title())

    def _update_engine_visibility(self):
        engine = self.combo_engine.get_active_text()
        if engine == "Vosk":
            self.vosk_row.show_all()
            self.whisper_row.hide()
        else:
            self.vosk_row.hide()
            self.whisper_row.show_all()

    def _on_engine_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self._set_temp("speech_engine", text)
            self._update_engine_visibility()

    def _on_whisper_size_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self._set_temp("whisper_model_size", text)

    def _on_device_changed(self, combo):
        idx = combo.get_active()
        if idx >= 0 and self.sources:
            self._set_temp("audio_device", self.sources[idx].name)

    def _on_vosk_model_changed(self, combo):
        text = combo.get_active_text()
        if text:
            model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
            self._set_temp("model_path", os.path.join(model_dir, text))

    def _on_auto_calibrate(self, widget):
        self.lbl_cal_result.set_text("Calibrating… stay quiet for 3 seconds.")
        widget.set_sensitive(False)

        def _run():
            try:
                from .mic_enhancer import MicEnhancer
                enh = MicEnhancer(self.settings)
                result = enh.auto_calibrate()
                recommended = result.get("recommended_threshold", 500)
                GLib.idle_add(self.lbl_cal_result.set_text,
                              f"✅ Noise floor: {result.get('noise_floor', 0):.0f} RMS → threshold: {recommended}")
                GLib.idle_add(self.spin_thresh.set_value, float(recommended))
                GLib.idle_add(self._set_temp, "silence_threshold", recommended)
                GLib.idle_add(self.settings.set, "silence_threshold", recommended)
            except Exception as e:
                GLib.idle_add(self.lbl_cal_result.set_text, f"❌ Calibration failed: {e}")
            finally:
                GLib.idle_add(widget.set_sensitive, True)

        import threading
        threading.Thread(target=_run, daemon=True).start()



    def _on_toggle_test(self, widget):
        if self.is_testing:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        """Start recording — user pushes button again to stop."""
        self.is_testing = True
        self.recorded_frames = []
        self.btn_test.set_label("⏳  Starting…")
        self.btn_test.set_sensitive(False)

        import threading
        threading.Thread(target=self._start_test_bg, daemon=True).start()

    def _start_test_bg(self):
        """Background thread: init PyAudio + open stream (ALSA probe is slow)."""
        import pyaudio
        try:
            self.pa = pyaudio.PyAudio()

            def _audio_callback(in_data, frame_count, time_info, status):
                if in_data:
                    self.recorded_frames.append(in_data)
                return (None, pyaudio.paContinue)

            self.test_stream = self.pa.open(format=pyaudio.paInt16, channels=1,
                                            rate=16000, input=True, frames_per_buffer=1024,
                                            stream_callback=_audio_callback)
            GLib.idle_add(self.btn_test.set_label, "⏹  Stop")
            GLib.idle_add(self.btn_test.set_sensitive, True)
            GLib.idle_add(lambda: GLib.timeout_add(100, self._update_level))
            logger.info("Test recording started")
        except Exception as e:
            logger.error(f"Failed to start test stream: {e}")
            self.is_testing = False
            GLib.idle_add(self.btn_test.set_label, "▶  Record")
            GLib.idle_add(self.btn_test.set_sensitive, True)

    def _stop_test(self):
        self.is_testing = False
        if getattr(self, "test_stream", None):
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None

        if getattr(self, "pa", None):
            self.pa.terminate()
            self.pa = None

        if getattr(self, "recorded_frames", None) and self.recorded_frames:
            import threading
            frames = list(self.recorded_frames)
            self.recorded_frames = []
            threading.Thread(target=self._play_playback, args=(frames,)).start()
        else:
            self.btn_test.set_label("▶  Record")

    def _play_playback(self, frames):
        import pyaudio
        GLib.idle_add(self.btn_test.set_label, "🔊  Playing…")
        GLib.idle_add(self.btn_test.set_sensitive, False)
        pa = None
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
            for fr in frames:
                stream.write(fr)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            if pa:
                pa.terminate()
            GLib.idle_add(self.btn_test.set_label, "▶  Record")
            GLib.idle_add(self.btn_test.set_sensitive, True)

    def _update_level(self):
        if not self.is_testing:
            self.level_bar.set_value(0)
            return False

        try:
            if self.recorded_frames:
                data = self.recorded_frames[-1]
                from src.c_ext import rms_int16
                rms = rms_int16(data)
                self.level_bar.set_value(min(rms / 10000.0, 1.0))
        except Exception:
            pass

        return True

    # ── Live volume + enhancement handlers ──────────────────────────────

    def _on_mic_volume_changed(self, widget):
        """Apply mic volume change immediately via pactl."""
        val = int(widget.get_value())
        self._set_temp("mic_volume", val)
        try:
            from .mic_enhancer import MicEnhancer
            enhancer = MicEnhancer(self.settings)
            enhancer.set_input_volume(val)
        except Exception as e:
            logger.warning(f"Live mic volume apply: {e}")

    def _on_spk_volume_changed(self, widget):
        """Apply speaker volume change immediately via pactl."""
        val = int(widget.get_value())
        self._set_temp("speaker_volume", val)
        try:
            from .mic_enhancer import MicEnhancer
            enhancer = MicEnhancer(self.settings)
            enhancer.set_output_volume(val)
        except Exception as e:
            logger.warning(f"Live speaker volume apply: {e}")

    def _on_webrtc_toggled(self, widget):
        """Apply WebRTC noise suppression change immediately."""
        active = widget.get_active()
        self._set_temp("noise_suppression", active)
        # Grey out + uncheck sub-features when off, restore when on
        if hasattr(self, '_webrtc_sub_box'):
            self._webrtc_sub_box.set_sensitive(active)
            if active:
                self.check_hpf.set_active(self.settings.get("webrtc_high_pass_filter", True))
                self.check_vad.set_active(self.settings.get("webrtc_voice_detection", True))
                self.check_dgc.set_active(self.settings.get("webrtc_digital_gain", True))
                self.check_agc.set_active(self.settings.get("webrtc_analog_gain", False))
            else:
                self.check_hpf.set_active(False)
                self.check_vad.set_active(False)
                self.check_dgc.set_active(False)
                self.check_agc.set_active(False)
        try:
            from .mic_enhancer import MicEnhancer
            enhancer = MicEnhancer(self.settings)
            if active:
                # Mutual exclusion: disable RNNoise if it's on
                if hasattr(self, 'check_rnnoise') and self.check_rnnoise.get_active():
                    enhancer.disable_rnnoise()
                    self.check_rnnoise.set_active(False)
                enhancer.enable_noise_suppression()
            else:
                enhancer.disable_noise_suppression()
        except Exception as e:
            logger.warning(f"Live WebRTC toggle: {e}")

    def _on_webrtc_sub_toggled(self, key, widget):
        """Apply a WebRTC sub-feature change — save and reload module."""
        active = widget.get_active()
        self._set_temp(key, active)
        self.settings.set(key, active)
        # Reload module with new args if noise suppression is active
        if self.temp_settings.get("noise_suppression", False):
            try:
                from .mic_enhancer import MicEnhancer
                enhancer = MicEnhancer(self.settings)
                enhancer.enable_noise_suppression()
            except Exception as e:
                logger.warning(f"WebRTC sub-feature reload: {e}")

    def _on_rnnoise_toggled(self, widget):
        """Toggle RNNoise AI denoiser — mutually exclusive with WebRTC."""
        active = widget.get_active()
        self._set_temp("rnnoise_enabled", active)
        try:
            from .mic_enhancer import MicEnhancer
            enhancer = MicEnhancer(self.settings)
            if active:
                # Disable WebRTC first (mutual exclusion)
                if self.temp_settings.get("noise_suppression", False):
                    enhancer.disable_noise_suppression()
                    self._set_temp("noise_suppression", False)
                    self.check_noise.set_active(False)
                enhancer.enable_rnnoise()
            else:
                enhancer.disable_rnnoise()
        except Exception as e:
            logger.warning(f"RNNoise toggle: {e}")

    def _on_easyeffects_clicked(self, widget):
        """Launch EasyEffects or show install instructions."""
        from .mic_enhancer import MicEnhancer
        if not MicEnhancer.is_easyeffects_installed():
            # Show install dialog
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="EasyEffects Not Installed"
            )
            dialog.format_secondary_text(
                "Install via terminal:\n\n"
                "  sudo apt install easyeffects\n\n"
                "EasyEffects provides parametric EQ, compressor,\n"
                "noise gate, and de-esser for your microphone."
            )
            dialog.run()
            dialog.destroy()
        else:
            MicEnhancer.launch_easyeffects()
            widget.set_label("🎛️  EasyEffects — Running ✅")

    def _close(self, save: bool):
        if save:
            self.save_settings()
        self._stop_test()
        self.destroy()

    def _on_delete(self, *_):
        self._close(save=False)
        return False

    def save_settings(self):
        changes = False
        reinit_engine = False

        new_device = self.temp_settings.get("audio_device")
        old_device = self.settings.get("audio_device")
        if new_device != old_device and new_device:
            try:
                from .pulseaudio_helper import set_default_source
                set_default_source(new_device)
            except ImportError:
                pass

        for key, value in self.temp_settings.items():
            if self.settings.get(key) != value:
                self.settings.set(key, value)
                changes = True
                if key in ["speech_engine", "whisper_model_size", "model_path"]:
                    reinit_engine = True

        if changes and self.engine_change_callback and reinit_engine:
            self.engine_change_callback()

        # Apply log level change at runtime
        if changes and "log_level" in self.temp_settings:
            try:
                from .logger import set_log_level
                set_log_level(self.temp_settings["log_level"])
            except Exception:
                pass

        # Refresh tray mode indicator if mode or key changed
        if changes and hasattr(self, '_tray_app') and self._tray_app:
            try:
                self._tray_app.update_mode_label(self.settings)
            except Exception:
                pass

    def destroy(self):
        self._stop_test()
        super().destroy()



# End of SettingsDialog
