import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib, GObject
import threading
import os
import signal

# Constants
APP_ID = "com.voxinput.app"
ICON_IDLE = "microphone-sensitivity-medium-symbolic" # Standard GNOME icon
ICON_ACTIVE = "microphone-sensitivity-high-symbolic"

class SystemTrayApp:
    def __init__(self, toggle_callback, quit_callback):
        self.toggle_callback = toggle_callback
        self.quit_callback = quit_callback
        self.is_listening = False
        
        # Create Indicator
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_IDLE,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self._build_menu()

    def _build_menu(self):
        menu = Gtk.Menu()
        
        # Toggle Item
        self.item_toggle = Gtk.MenuItem(label="Start Listening")
        self.item_toggle.connect('activate', self._on_toggle)
        menu.append(self.item_toggle)
        
        # Quit Item
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect('activate', self._on_quit)
        menu.append(item_quit)
        
        menu.show_all()
        self.indicator.set_menu(menu)

    def _on_toggle(self, _):
        self.toggle_callback()

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
        # GTK4 main loop
        # Note: AppIndicator with GTK4 is tricky, might need GTK3 if GTK4 binds are missing.
        # Ubuntu 24.04 usually supports both. Let's try Gtk.main() for GTK3 compat or new loop.
        # Actually AppIndicator usually works best with GTK3 still for tray.
        # But let's see. If this crashes, I'll switch to GTK3.
        # Many tray libs still rely on GTK3.
        
        # Checking imports above: gi.require_version('Gtk', '4.0')
        # Gtk 4 removed Gtk.Menu. It uses Gtk.Popover or GMenuModel.
        # AppIndicator often needs Gtk.Menu (GTK3).
        # SWITCHING TO GTK 3 for safety and compatibility with AppIndicator.
        pass

# Switch implementation below to GTK 3.0 safely
