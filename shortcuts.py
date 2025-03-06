import platform
import ctypes
import ctypes.wintypes as wintypes
from PyQt5.QtCore import QAbstractNativeEventFilter

# Windows constants
WM_HOTKEY = 0x0312


class ShortcutBackend:
    def install_shortcut(self, modifiers, key, shortcut_id, callback):
        """Install a system-level shortcut (backend-specific)."""
        raise NotImplementedError

    def remove_shortcut(self, shortcut_id):
        """Remove a system-level shortcut (backend-specific)."""
        raise NotImplementedError

    def process_message(self, msg):
        """Process system messages for shortcut events."""
        raise NotImplementedError

    def install_event_handler(self, app):
        """Set up platform-specific event handling."""
        raise NotImplementedError


class WindowsShortcutBackend(ShortcutBackend):
    MODIFIER_MAP = {"ctrl": 0x0002, "alt": 0x0001, "shift": 0x0004, "win": 0x0008}
    KEY_MAP = {
        "a": 0x41,
        "b": 0x42,
        "c": 0x43,
        "d": 0x44,
        "e": 0x45,
        "f": 0x46,
        "g": 0x47,
        "h": 0x48,
        "i": 0x49,
        "j": 0x4A,
        "k": 0x4B,
        "l": 0x4C,
        "m": 0x4D,
        "n": 0x4E,
        "o": 0x4F,
        "p": 0x50,
        "q": 0x51,
        "r": 0x52,
        "s": 0x53,
        "t": 0x54,
        "u": 0x55,
        "v": 0x56,
        "w": 0x57,
        "x": 0x58,
        "y": 0x59,
        "z": 0x5A,
        "0": 0x30,
        "1": 0x31,
        "2": 0x32,
        "3": 0x33,
        "4": 0x34,
        "5": 0x35,
        "6": 0x36,
        "7": 0x37,
        "8": 0x38,
        "9": 0x39,
    }

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.shortcuts = {}

    def install_shortcut(self, modifiers, key, shortcut_id, callback):
        mod_value = sum(self.MODIFIER_MAP.get(m, 0) for m in modifiers)
        key_value = self.KEY_MAP.get(key.lower(), 0)
        if not key_value:
            raise ValueError(f"Unsupported key: {key}")
        if not all(m in self.MODIFIER_MAP for m in modifiers):
            raise ValueError(
                f"Unsupported modifiers: {set(modifiers) - set(self.MODIFIER_MAP)}"
            )
        if self.user32.RegisterHotKey(None, shortcut_id, mod_value, key_value):
            self.shortcuts[shortcut_id] = callback
            return True
        return False

    def remove_shortcut(self, shortcut_id):
        if shortcut_id in self.shortcuts and self.user32.UnregisterHotKey(
            None, shortcut_id
        ):
            del self.shortcuts[shortcut_id]
            return True
        return False

    def process_message(self, msg):
        if msg.message == WM_HOTKEY and msg.wParam in self.shortcuts:
            self.shortcuts[msg.wParam]()
            return True
        return False

    def install_event_handler(self, app):
        class WindowsEventFilter(QAbstractNativeEventFilter):
            def __init__(self, backend):
                super().__init__()
                self.backend = backend

            def nativeEventFilter(self, eventType, message):
                if eventType == b"windows_generic_MSG":
                    msg = ctypes.cast(
                        ctypes.c_void_p(int(message)), ctypes.POINTER(wintypes.MSG)
                    ).contents
                    if self.backend.process_message(msg):
                        return True, 0
                return False, 0

        self.event_filter = WindowsEventFilter(self)
        app.installNativeEventFilter(self.event_filter)


class ShortcutManager:
    @staticmethod
    def get_backend():
        """Determine the platform-specific backend."""
        if platform.system() == "Windows":
            return WindowsShortcutBackend()
        raise NotImplementedError(f"Unsupported platform: {platform.system()}")

    def __init__(self, app, shortcuts_dict, callback_map):
        """Initialize with app, shortcuts dictionary, and callback map."""
        self.backend = self.get_backend()
        self.next_id = 1
        self.shortcuts_dict = shortcuts_dict
        self.callback_map = callback_map
        self.backend.install_event_handler(app)
        self.setup_platform_shortcuts()

    def setup_platform_shortcuts(self):
        """Set up shortcuts for the current platform from the dictionary."""
        platform_key = platform.system().lower()
        platform_shortcuts = self.shortcuts_dict.get(platform_key, [])
        for shortcut in platform_shortcuts:
            try:
                callback = self.callback_map.get(shortcut["action"])
                if callback:
                    self.assign_shortcut(shortcut["shortcut_str"], callback)
                    print(
                        f"Shortcut {shortcut['shortcut_str']} assigned successfully to {shortcut['action']}"
                    )
                else:
                    print(f"No callback found for action: {shortcut['action']}")
            except ValueError as e:
                print(f"Shortcut assignment failed: {e}")

    def assign_shortcut(self, shortcut_str, callback):
        """Assign a shortcut by parsing the string and delegating to the backend."""
        parts = shortcut_str.lower().split("+")
        if not parts:
            raise ValueError(f"Invalid shortcut string: {shortcut_str}")
        modifiers = parts[:-1]
        key = parts[-1]
        shortcut_id = self.next_id
        if self.backend.install_shortcut(modifiers, key, shortcut_id, callback):
            self.next_id += 1
            return shortcut_id
        raise ValueError(f"Failed to assign shortcut: {shortcut_str}")

    def unassign_shortcut(self, shortcut_id):
        """Unassign a specific shortcut by ID."""
        return self.backend.remove_shortcut(shortcut_id)

    def cleanup(self):
        """Clean up all shortcuts and reset state."""
        self.backend.shortcuts.clear()
        self.next_id = 1
