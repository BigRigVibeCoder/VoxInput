import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject
import os
import signal
import threading
import logging
import subprocess
from .audio import MicTester

logger = logging.getLogger(__name__)

# Constants
APP_ID = "com.voxinput.app"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Icons
ICON_GREEN = os.path.join(BASE_DIR, "icons", "green_mic.png")
ICON_RED = os.path.join(BASE_DIR, "icons", "red_mic.png")
ICON_WHITE = os.path.join(BASE_DIR, "icons", "white_mic.png")
# Fallback if PNGs fail to load
ICON_IDLE_FALLBACK = "microphone-sensitivity-medium-symbolic"
ICON_ACTIVE_FALLBACK = "microphone-sensitivity-high-symbolic"

class SettingsWindow(Gtk.Window):
    def __init__(self, input_devices, current_device_index, current_engine, on_save_callback, on_toggle_callback, is_listening, quit_callback):
        Gtk.Window.__init__(self, title="VoxInput Settings")
        self.set_border_width(10)
        self.set_default_size(450, 350)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        
        self.input_devices = input_devices
        self.selected_device_index = current_device_index
        self.selected_engine = current_engine
        self.on_save_callback = on_save_callback
        self.on_toggle_callback = on_toggle_callback
        self.quit_callback = quit_callback
        
        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)
        
        # Tabs
        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)
        
        # --- Tab 1: Controls ---
        tab1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        tab1_box.set_border_width(20)
        tab1_box.set_halign(Gtk.Align.CENTER)
        tab1_box.set_valign(Gtk.Align.CENTER)
        
        self.lbl_status = Gtk.Label(label="Status: " + ("Listening" if is_listening else "Idle"))
        # Increase font size for status
        self.lbl_status.set_markup(f"<span size='large' weight='bold'>{'Listening' if is_listening else 'Idle'}</span>")
        tab1_box.pack_start(self.lbl_status, False, False, 0)
        
        self.btn_toggle = Gtk.Button(label="Stop Listening" if is_listening else "Start Listening")
        self.btn_toggle.set_size_request(200, 60)
        self.btn_toggle.connect("clicked", self._on_toggle_click)
        # Style logic to be added if css needed, but basic label update is fine
        tab1_box.pack_start(self.btn_toggle, False, False, 0)
        
        notebook.append_page(tab1_box, Gtk.Label(label="Controls"))
        
        # --- Tab 2: Recognition Engine ---
        tab2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab2_box.set_border_width(15)
        
        lbl_eng = Gtk.Label(label="Select Recognition Engine:")
        lbl_eng.set_halign(Gtk.Align.START)
        tab2_box.pack_start(lbl_eng, False, False, 0)
        
        # Engine Radio Buttons
        self.eng_vosk = Gtk.RadioMenuItem(label="Vosk (Fast, Low CPU)") # reusing RadioMenuItem logic visually or RadioButton?
        # Use Gtk.RadioButton for window UI
        self.rb_vosk = Gtk.RadioButton.new_with_label_from_widget(None, "Vosk (Fast, Low CPU)")
        self.rb_vosk.connect("toggled", self._on_engine_toggled, "vosk")
        tab2_box.pack_start(self.rb_vosk, False, False, 0)
        
        self.rb_whisper = Gtk.RadioButton.new_with_label_from_widget(self.rb_vosk, "Whisper (High Accuracy, Slower)")
        self.rb_whisper.connect("toggled", self._on_engine_toggled, "whisper")
        tab2_box.pack_start(self.rb_whisper, False, False, 0)
        
        # Set active
        if self.selected_engine == "whisper":
            self.rb_whisper.set_active(True)
        else:
            self.rb_vosk.set_active(True)
            
        notebook.append_page(tab2_box, Gtk.Label(label="Engine"))
        
        # --- Tab 3: Microphone ---
        tab3_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab3_box.set_border_width(15)
        
        lbl_mic = Gtk.Label(label="Select Input Device:")
        lbl_mic.set_halign(Gtk.Align.START)
        tab3_box.pack_start(lbl_mic, False, False, 0)
        
        # Scrolled Window for Mics
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        tab3_box.pack_start(scrolled, True, True, 0)
        
        mic_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(mic_list_box)
        
        # Mic Radio Buttons
        self.mic_group = None
        
        # Default
        rb_def = Gtk.RadioButton.new_with_label_from_widget(None, "System Default")
        rb_def.connect("toggled", self._on_mic_toggled, None)
        mic_list_box.pack_start(rb_def, False, False, 0)
        self.mic_group = rb_def
        if self.selected_device_index is None:
            rb_def.set_active(True)
            
        for idx, name in self.input_devices:
            rb = Gtk.RadioButton.new_with_label_from_widget(self.mic_group, f"{name} ({idx})")
            rb.connect("toggled", self._on_mic_toggled, idx)
            mic_list_box.pack_start(rb, False, False, 0)
            if self.selected_device_index == idx:
                rb.set_active(True)

        notebook.append_page(tab3_box, Gtk.Label(label="Microphone"))
        
        # Test Mic Section
        box_test = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_test.set_halign(Gtk.Align.START)
        
        self.btn_test_mic = Gtk.Button(label="Test Microphone (5s)")
        self.btn_test_mic.connect("clicked", self._on_test_mic_clicked)
        box_test.pack_start(self.btn_test_mic, False, False, 0)
        
        self.lbl_test_status = Gtk.Label(label="")
        box_test.pack_start(self.lbl_test_status, False, False, 0)
        
        tab3_box.pack_start(box_test, False, False, 0)

        # --- Footer Actions ---
        hbox_footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox_footer.set_halign(Gtk.Align.END)
        vbox.pack_start(hbox_footer, False, False, 5)
        
        btn_app_quit = Gtk.Button(label="Quit App")
        btn_app_quit.get_style_context().add_class("destructive-action")
        btn_app_quit.connect("clicked", lambda x: self.quit_callback())
        hbox_footer.pack_start(btn_app_quit, False, False, 0)

        btn_save = Gtk.Button(label="Save & Close")
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self._on_save_clicked)
        hbox_footer.pack_start(btn_save, False, False, 0)

    def _on_toggle_click(self, widget):
        self.on_toggle_callback()
        # State update will handle label change via update_state calls if needed, 
        # but simpler to just toggle logically here. 
        # The app should call update_ui_state ideally.
        
    def _on_engine_toggled(self, button, engine_id):
        if button.get_active():
            self.selected_engine = engine_id
            
    def _on_mic_toggled(self, button, device_index):
        if button.get_active():
            self.selected_device_index = device_index

    def _on_test_mic_clicked(self, widget):
        self.btn_test_mic.set_sensitive(False)
        self.lbl_test_status.set_text("Initializing...")
        
        # Run in thread
        t = threading.Thread(target=self._run_mic_test)
        t.daemon = True
        t.start()

    def _run_mic_test(self):
        tester = MicTester(self.selected_device_index)
        
        def update_ui(msg):
            GLib.idle_add(self.lbl_test_status.set_text, msg)
            if msg == "Done" or msg.startswith("Error"):
                 GLib.idle_add(self.btn_test_mic.set_sensitive, True)

        tester.run_test(duration=5, progress_callback=update_ui)

    def _on_save_clicked(self, widget):
        # Call save with current selections
        self.on_save_callback(self.selected_engine, self.selected_device_index)
        self.destroy()

    def update_listening_state(self, is_listening):
        txt = "Listening" if is_listening else "Idle"
        self.lbl_status.set_markup(f"<span size='large' weight='bold'>{txt}</span>")
        self.btn_toggle.set_label("Stop Listening" if is_listening else "Start Listening")


class SystemTrayApp:
    def __init__(self, toggle_callback, quit_callback, input_devices=None, 
                 on_device_changed=None, current_device_index=None, 
                 on_engine_changed=None, current_engine="vosk"):
        
        # Store all data needed for the window
        self.toggle_callback = toggle_callback
        self.quit_callback = quit_callback
        self.input_devices = input_devices or []
        self.on_save_device = on_device_changed
        self.on_save_engine = on_engine_changed
        
        self.current_device_index = current_device_index
        self.current_engine = current_engine
        self.is_listening = False
        
        self.window = None

        # Preload Icons as Pixbufs
        self.icon_pixbufs = {}
        try:
             from gi.repository import GdkPixbuf
             self.icon_pixbufs[ICON_GREEN] = GdkPixbuf.Pixbuf.new_from_file(ICON_GREEN)
             self.icon_pixbufs[ICON_RED] = GdkPixbuf.Pixbuf.new_from_file(ICON_RED)
             self.icon_pixbufs[ICON_WHITE] = GdkPixbuf.Pixbuf.new_from_file(ICON_WHITE)
        except Exception as e:
             logging.error(f"Failed to load icon pixbufs: {e}")

        # Create Status Icon
        self.icon = Gtk.StatusIcon()
        self.icon.set_title("VoxInput")
        self.icon.set_tooltip_text("VoxInput: Idle")
        
        # Connect Signals
        self.icon.connect('activate', self._on_activate)
        self.icon.connect('popup-menu', self._on_popup_menu)
        
        # Set Initial Icon
        self._set_icon(ICON_GREEN, ICON_IDLE_FALLBACK)
        
        # Tray Menu
        self._build_tray_menu()
        
        # Flashing
        self.flash_timer = None
        self.flash_count = 0
        self.flash_target_state = False

    def _build_tray_menu(self):
        self.menu = Gtk.Menu()
        
        # 1. Start/Stop Listening (Top Item for Quick Access/Default)
        self.item_toggle = Gtk.MenuItem(label="Start Listening (Ctrl+Alt+M)")
        self.item_toggle.connect('activate', lambda _: self.toggle_callback())
        self.menu.append(self.item_toggle)
        
        self.menu.append(Gtk.SeparatorMenuItem())

        # 2. Open Settings
        item_settings = Gtk.MenuItem(label="Open Settings")
        item_settings.connect('activate', lambda _: self.open_settings_window())
        self.menu.append(item_settings)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # 3. Quit
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect('activate', lambda _: self.quit_callback())
        self.menu.append(item_quit)
        
        self.menu.show_all()

    def _on_activate(self, widget):
        # Left Click -> Toggle Listening
        self.toggle_callback()

    def _on_popup_menu(self, icon, button, time):
        # Right Click -> Show Menu
        self.menu.show_all()
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

    def open_settings_window(self):
        if self.window:
            self.window.present()
            return
            
        self.window = SettingsWindow(
            input_devices=self.input_devices,
            current_device_index=self.current_device_index,
            current_engine=self.current_engine,
            on_save_callback=self._on_window_save,
            on_toggle_callback=self.toggle_callback,
            is_listening=self.is_listening,
            quit_callback=self.quit_callback
        )
        self.window.connect("destroy", self._on_window_destroyed)
        self.window.show_all()

    def _on_window_save(self, engine, device_index):
        # Update local state
        self.current_engine = engine
        self.current_device_index = device_index
        
        # Call app callbacks
        if self.on_save_engine:
            self.on_save_engine(engine)
        if self.on_save_device:
            self.on_save_device(device_index)

    def _on_window_destroyed(self, widget):
        self.window = None

    def set_listening_state(self, is_listening):
        self.is_listening = is_listening
        
        # Update Window if open
        if self.window:
            GLib.idle_add(self.window.update_listening_state, is_listening)
        
        # Cancel any existing timer just in case
        if self.flash_timer:
            try:
                GLib.source_remove(self.flash_timer)
            except:
                pass
            self.flash_timer = None
            
        def _update_ui():
            # Update Menu Label & Tooltip & Icon Directly
            if self.is_listening:
                 self.item_toggle.set_label("Stop Listening (Ctrl+Alt+M)")
                 self.icon.set_tooltip_text("VoxInput: Listening")
                 self._set_icon(ICON_RED, ICON_ACTIVE_FALLBACK)
                 self._notify_user("Listening Started", "microphone-sensitivity-high")
                 self._play_sound("on")
            else:
                 self.item_toggle.set_label("Start Listening (Ctrl+Alt+M)")
                 self.icon.set_tooltip_text("VoxInput: Idle")
                 self._set_icon(ICON_GREEN, ICON_IDLE_FALLBACK)
                 self._notify_user("Listening Stopped", "microphone-sensitivity-muted")
                 self._play_sound("off")
        
        GLib.idle_add(_update_ui)

    def _notify_user(self, title, icon_name):
        try:
             # Ensure Notify is initialized (import at top but init here safely)
             # We assume gi.repository.Notify is available or we add it.
             # If not imported, we need to add imports.
             # For now, simplistic implementation assuming Notify exists or we use Gtk Message?
             # Better: Use subprocess-notify-send if Notify lib not handy, avoids segfaults.
             subprocess.Popen(['notify-send', '-i', icon_name, 'VoxInput', title])
        except Exception as e:
            pass # Ignore notification errors

    def _play_sound(self, state):
        try:
            # Simple beep tones using paplay (PulseAudio) and standard sounds
            # On: complete.oga or message.oga
            # Off: suspend-error.oga or similar
            # Adjust paths to common Ubuntu sounds
            sound_path = ""
            if state == "on":
                sound_path = "/usr/share/sounds/freedesktop/stereo/service-login.oga"
            else:
                sound_path = "/usr/share/sounds/freedesktop/stereo/service-logout.oga"
            
            if os.path.exists(sound_path):
                subprocess.Popen(['paplay', sound_path])
        except Exception:
            pass

    # _flash_step removed as it is no longer used

    def _set_icon(self, path, fallback):
        # logging.info(f"Setting icon to: {path}") # Debug
        if path in self.icon_pixbufs:
             self.icon.set_from_pixbuf(self.icon_pixbufs[path])
        elif os.path.exists(path):
            self.icon.set_from_file(path)
        else:
            self.icon.set_from_icon_name(fallback)
