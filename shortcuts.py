import platform
import ctypes
import ctypes.util
from PyQt5.QtCore import QAbstractNativeEventFilter

if platform.system() == "Windows":
    import ctypes.wintypes as wintypes

    # Windows constants
    WM_HOTKEY = 0x0312


class ShortcutBackend:
    def install_shortcut(self, modifiers, key, shortcut_id, callback):
        raise NotImplementedError

    def remove_shortcut(self, shortcut_id):
        raise NotImplementedError

    def process_message(self, msg):
        raise NotImplementedError

    def install_event_handler(self, app):
        raise NotImplementedError

    def teardown(self):
        """Release any resources held by the backend."""
        return None


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
        self.event_filter = None
        self._app = None

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

        self._app = app
        self.event_filter = WindowsEventFilter(self)
        app.installNativeEventFilter(self.event_filter)

    def teardown(self):
        for shortcut_id in list(self.shortcuts.keys()):
            self.remove_shortcut(shortcut_id)
        if self._app and self.event_filter:
            try:
                self._app.removeNativeEventFilter(self.event_filter)
            except Exception:
                pass
        self.event_filter = None
        self._app = None


class MacShortcutBackend(ShortcutBackend):
    MODIFIER_MAP = {
        "ctrl": 1 << 12,
        "control": 1 << 12,
        "alt": 1 << 11,
        "option": 1 << 11,
        "shift": 1 << 9,
        "cmd": 1 << 8,
        "win": 1 << 8,
        "super": 1 << 8,
    }

    KEY_MAP = {
        "a": 0x00,
        "b": 0x0B,
        "c": 0x08,
        "d": 0x02,
        "e": 0x0E,
        "f": 0x03,
        "g": 0x05,
        "h": 0x04,
        "i": 0x22,
        "j": 0x26,
        "k": 0x28,
        "l": 0x25,
        "m": 0x2E,
        "n": 0x2D,
        "o": 0x1F,
        "p": 0x23,
        "q": 0x0C,
        "r": 0x0F,
        "s": 0x01,
        "t": 0x11,
        "u": 0x20,
        "v": 0x09,
        "w": 0x0D,
        "x": 0x07,
        "y": 0x10,
        "z": 0x06,
        "0": 0x1D,
        "1": 0x12,
        "2": 0x13,
        "3": 0x14,
        "4": 0x15,
        "5": 0x17,
        "6": 0x16,
        "7": 0x1A,
        "8": 0x1C,
        "9": 0x19,
    }

    kEventClassKeyboard = 0x6B657962
    kEventHotKeyPressed = 6
    kEventParamDirectObject = 0x2D2D2D2D
    typeEventHotKeyID = 0x686B6964

    class EventTypeSpec(ctypes.Structure):
        _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]

    class EventHotKeyID(ctypes.Structure):
        _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]

    EventHandlerUPP = ctypes.CFUNCTYPE(
        ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
    )

    def __init__(self):
        carbon_path = ctypes.util.find_library("Carbon")
        if not carbon_path:
            raise RuntimeError("Carbon framework not found")
        self.carbon = ctypes.CDLL(carbon_path)
        self.carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
        self.carbon.InstallApplicationEventHandler.argtypes = [
            self.EventHandlerUPP,
            ctypes.c_uint32,
            ctypes.POINTER(self.EventTypeSpec),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.carbon.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(self.EventHotKeyID),
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.carbon.RegisterEventHotKey.restype = ctypes.c_int32
        self.carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
        self.carbon.UnregisterEventHotKey.restype = ctypes.c_int32
        self.carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]
        self.carbon.RemoveEventHandler.restype = ctypes.c_int32
        self.carbon.GetEventParameter.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        ]
        self.carbon.GetEventParameter.restype = ctypes.c_int32

        self.shortcuts = {}
        self.hotkey_refs = {}
        self.event_handler_ref = ctypes.c_void_p()
        self.event_target = self.carbon.GetApplicationEventTarget()
        self._handler_proc = self.EventHandlerUPP(self._handle_hotkey)
        self._install_event_handler()

    def _install_event_handler(self):
        event_types = (self.EventTypeSpec * 1)(
            self.EventTypeSpec(self.kEventClassKeyboard, self.kEventHotKeyPressed)
        )
        status = self.carbon.InstallApplicationEventHandler(
            self._handler_proc,
            1,
            event_types,
            None,
            ctypes.byref(self.event_handler_ref),
        )
        if status != 0:
            raise RuntimeError(f"Failed to install hotkey handler (status={status})")

    def _handle_hotkey(self, handler_call_ref, event_ref, user_data):
        hotkey_id = self.EventHotKeyID()
        status = self.carbon.GetEventParameter(
            event_ref,
            self.kEventParamDirectObject,
            self.typeEventHotKeyID,
            None,
            ctypes.sizeof(hotkey_id),
            None,
            ctypes.byref(hotkey_id),
        )
        if status == 0:
            callback = self.shortcuts.get(hotkey_id.id)
            if callback:
                callback()
        return 0

    def install_shortcut(self, modifiers, key, shortcut_id, callback):
        mod_value = 0
        invalid_mods = [m for m in modifiers if m not in self.MODIFIER_MAP]
        if invalid_mods:
            raise ValueError(f"Unsupported modifiers: {set(invalid_mods)}")
        for mod in modifiers:
            mod_value |= self.MODIFIER_MAP[mod]

        key_value = self.KEY_MAP.get(key.lower())
        if key_value is None:
            raise ValueError(f"Unsupported key: {key}")

        hotkey_id = self.EventHotKeyID(0x494D324C, shortcut_id)  # 'IM2L'
        hotkey_ref = ctypes.c_void_p()
        status = self.carbon.RegisterEventHotKey(
            key_value,
            mod_value,
            ctypes.byref(hotkey_id),
            self.event_target,
            0,
            ctypes.byref(hotkey_ref),
        )
        if status == 0:
            self.shortcuts[shortcut_id] = callback
            self.hotkey_refs[shortcut_id] = hotkey_ref
            return True
        return False

    def remove_shortcut(self, shortcut_id):
        hotkey_ref = self.hotkey_refs.get(shortcut_id)
        if not hotkey_ref:
            return False
        status = self.carbon.UnregisterEventHotKey(hotkey_ref)
        if status == 0:
            del self.hotkey_refs[shortcut_id]
            del self.shortcuts[shortcut_id]
            return True
        return False

    def process_message(self, msg):
        return False

    def install_event_handler(self, app):
        # Carbon handler installed during initialization; nothing to do here.
        return None

    def teardown(self):
        for shortcut_id in list(self.shortcuts.keys()):
            self.remove_shortcut(shortcut_id)
        if self.event_handler_ref:
            try:
                self.carbon.RemoveEventHandler(self.event_handler_ref)
            except Exception:
                pass
            self.event_handler_ref = ctypes.c_void_p()
        self.hotkey_refs.clear()
        self.shortcuts.clear()


class LinuxShortcutBackend(ShortcutBackend):
    SHIFT_MASK = 1 << 0
    LOCK_MASK = 1 << 1
    CONTROL_MASK = 1 << 2
    MOD1_MASK = 1 << 3
    MOD2_MASK = 1 << 4
    MOD4_MASK = 1 << 6

    MODIFIER_MAP = {
        "shift": SHIFT_MASK,
        "ctrl": CONTROL_MASK,
        "control": CONTROL_MASK,
        "alt": MOD1_MASK,
        "mod1": MOD1_MASK,
        "win": MOD4_MASK,
        "super": MOD4_MASK,
    }

    class XErrorEvent(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_int),
            ("display", ctypes.c_void_p),
            ("resourceid", ctypes.c_ulong),
            ("serial", ctypes.c_ulong),
            ("error_code", ctypes.c_ubyte),
            ("request_code", ctypes.c_ubyte),
            ("minor_code", ctypes.c_ubyte),
            ("pad0", ctypes.c_ubyte),
        ]

    class XcbKeyEvent(ctypes.Structure):
        _fields_ = [
            ("response_type", ctypes.c_uint8),
            ("detail", ctypes.c_uint8),
            ("sequence", ctypes.c_uint16),
            ("time", ctypes.c_uint32),
            ("root", ctypes.c_uint32),
            ("event", ctypes.c_uint32),
            ("child", ctypes.c_uint32),
            ("root_x", ctypes.c_int16),
            ("root_y", ctypes.c_int16),
            ("event_x", ctypes.c_int16),
            ("event_y", ctypes.c_int16),
            ("state", ctypes.c_uint16),
            ("same_screen", ctypes.c_uint8),
            ("pad0", ctypes.c_uint8),
        ]

    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(XErrorEvent)
    )

    def __init__(self):
        x11_path = ctypes.util.find_library("X11")
        if not x11_path:
            raise RuntimeError("X11 library not found")
        self.xlib = ctypes.CDLL(x11_path)
        self.xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.xlib.XOpenDisplay.restype = ctypes.c_void_p
        self.xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.xlib.XDefaultRootWindow.restype = ctypes.c_uint32
        self.xlib.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.xlib.XStringToKeysym.restype = ctypes.c_ulong
        self.xlib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.xlib.XKeysymToKeycode.restype = ctypes.c_uint
        self.xlib.XGrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.xlib.XUngrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint32,
        ]
        self.xlib.XFlush.argtypes = [ctypes.c_void_p]
        self.xlib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.xlib.XSync.restype = ctypes.c_int
        self.xlib.XSetErrorHandler.argtypes = [ctypes.c_void_p]
        self.xlib.XSetErrorHandler.restype = ctypes.c_void_p
        self.xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.xlib.XCloseDisplay.restype = ctypes.c_int

        self.display = self.xlib.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Unable to open X11 display")
        self.root = self.xlib.XDefaultRootWindow(self.display)
        self.shortcuts = {}
        self.grab_masks = {}
        self.event_filter = None
        self._app = None
        self._last_error_code = None
        self._error_handler_proc = self.ERROR_HANDLER_FUNC(self._on_error)

    def _string_to_keycode(self, key):
        keysym = self.xlib.XStringToKeysym(key.encode("ascii"))
        if not keysym:
            keysym = self.xlib.XStringToKeysym(key.upper().encode("ascii"))
        if not keysym:
            raise ValueError(f"Unsupported key: {key}")
        keycode = int(self.xlib.XKeysymToKeycode(self.display, keysym))
        if keycode == 0:
            raise ValueError(f"Unable to resolve keycode for key: {key}")
        return keycode

    def _on_error(self, display, error_event):
        self._last_error_code = error_event.contents.error_code
        return 0

    def _with_error_trap(self, func, *args):
        self._last_error_code = None
        previous = self.xlib.XSetErrorHandler(self._error_handler_proc)
        try:
            result = func(*args)
            self.xlib.XSync(self.display, 0)
        finally:
            self.xlib.XSetErrorHandler(previous)
        return result, self._last_error_code

    def install_shortcut(self, modifiers, key, shortcut_id, callback):
        mod_value = 0
        invalid_mods = [m for m in modifiers if m not in self.MODIFIER_MAP]
        if invalid_mods:
            raise ValueError(f"Unsupported modifiers: {set(invalid_mods)}")
        for mod in modifiers:
            mod_value |= self.MODIFIER_MAP[mod]

        keycode = self._string_to_keycode(key)

        GrabModeAsync = 1
        owner_events = 1

        masks = [
            mod_value,
            mod_value | self.LOCK_MASK,
            mod_value | self.MOD2_MASK,
            mod_value | self.LOCK_MASK | self.MOD2_MASK,
        ]

        success = True
        registered_masks = []
        for mask in masks:
            _, error_code = self._with_error_trap(
                self.xlib.XGrabKey,
                self.display,
                keycode,
                mask,
                self.root,
                owner_events,
                GrabModeAsync,
                GrabModeAsync,
            )
            if error_code is not None:
                success = False
                break
            registered_masks.append(mask)

        self.xlib.XFlush(self.display)

        if success:
            self.shortcuts[shortcut_id] = {
                "callback": callback,
                "keycode": keycode,
                "modifiers": mod_value,
            }
            self.grab_masks[shortcut_id] = masks
            return True
        else:
            for registered_mask in registered_masks:
                self._with_error_trap(
                    self.xlib.XUngrabKey,
                    self.display,
                    keycode,
                    registered_mask,
                    self.root,
                )
            self.xlib.XFlush(self.display)
        return False

    def remove_shortcut(self, shortcut_id):
        if shortcut_id not in self.shortcuts:
            return False
        keycode = self.shortcuts[shortcut_id]["keycode"]
        masks = self.grab_masks.get(shortcut_id, [])
        for mask in masks:
            self._with_error_trap(
                self.xlib.XUngrabKey,
                self.display,
                keycode,
                mask,
                self.root,
            )
        self.xlib.XFlush(self.display)
        del self.shortcuts[shortcut_id]
        self.grab_masks.pop(shortcut_id, None)
        return True

    def process_message(self, msg):
        return False

    def _handle_key_event(self, keycode, state):
        normalized = state & ~(self.LOCK_MASK | self.MOD2_MASK)
        for shortcut in self.shortcuts.values():
            if (
                shortcut["keycode"] == keycode
                and shortcut["modifiers"] == normalized
            ):
                shortcut["callback"]()
                return True
        return False

    def install_event_handler(self, app):
        class LinuxEventFilter(QAbstractNativeEventFilter):
            XCB_KEY_PRESS = 2

            def __init__(self, backend):
                super().__init__()
                self.backend = backend

            def nativeEventFilter(self, eventType, message):
                if eventType in (b"xcb_generic_event_t", b"x11_generic_event"):
                    event = ctypes.cast(
                        ctypes.c_void_p(int(message)),
                        ctypes.POINTER(LinuxShortcutBackend.XcbKeyEvent),
                    ).contents
                    if event.response_type & 0x7F == self.XCB_KEY_PRESS:
                        if self.backend._handle_key_event(event.detail, event.state):
                            return True, 0
                return False, 0

        self.event_filter = LinuxEventFilter(self)
        app.installNativeEventFilter(self.event_filter)
        self._app = app

    def teardown(self):
        for shortcut_id in list(self.shortcuts.keys()):
            self.remove_shortcut(shortcut_id)
        if self._app and self.event_filter:
            try:
                self._app.removeNativeEventFilter(self.event_filter)
            except Exception:
                pass
        self.event_filter = None
        self._app = None
        if self.display:
            try:
                self.xlib.XCloseDisplay(self.display)
            except Exception:
                pass
            self.display = None


class ShortcutManager:
    @staticmethod
    def get_backend():
        system = platform.system()
        if system == "Windows":
            return WindowsShortcutBackend()
        if system == "Darwin":
            return MacShortcutBackend()
        if system == "Linux":
            return LinuxShortcutBackend()
        raise NotImplementedError(f"Unsupported platform: {platform.system()}")

    def __init__(self, app, shortcuts_dict, run_pipeline):
        self.backend = self.get_backend()
        self.next_id = 1
        self.shortcuts_dict = shortcuts_dict
        self.run_pipeline = run_pipeline  # Store the bound method
        self.backend.install_event_handler(app)
        self._action_shortcut_ids = {}
        self.setup_platform_shortcuts()

    def assign_shortcut(self, shortcut_str, callback):
        parts = shortcut_str.lower().split("+")
        if not parts:
            return False
        modifiers = parts[:-1]
        key = parts[-1]
        shortcut_id = self.next_id
        if self.backend.install_shortcut(modifiers, key, shortcut_id, callback):
            self.next_id += 1
            return shortcut_id
        return False

    def setup_platform_shortcuts(self):
        platform_key = platform.system().lower()
        candidate_keys = [platform_key]
        if platform_key == "darwin":
            candidate_keys.append("macos")
        elif platform_key == "windows":
            candidate_keys.extend(["win32", "win"])
        elif platform_key == "linux":
            candidate_keys.append("unix")
        candidate_keys.append("default")

        seen = set()
        for key in candidate_keys:
            shortcuts = self.shortcuts_dict.get(key, [])
            for shortcut in shortcuts:
                identifier = (shortcut["shortcut_str"], shortcut["action"])
                if identifier in seen:
                    continue
                seen.add(identifier)
                action = shortcut["action"]
                callback = lambda act=action: self.run_pipeline(act)
                shortcut_id = self.assign_shortcut(shortcut["shortcut_str"], callback)
                if shortcut_id:
                    print(
                        f"Registered shortcut '{shortcut['shortcut_str']}' for action '{action}' (ID: {shortcut_id})"
                    )
                    self._action_shortcut_ids.setdefault(action, []).append(shortcut_id)
                else:
                    print(f"Could not register shortcut '{shortcut['shortcut_str']}'")

    def unassign_shortcut(self, shortcut_id):
        removed = self.backend.remove_shortcut(shortcut_id)
        if removed:
            for ids in self._action_shortcut_ids.values():
                if shortcut_id in ids:
                    ids.remove(shortcut_id)
                    break
        return removed

    def cleanup(self):
        for ids in list(self._action_shortcut_ids.values()):
            for shortcut_id in list(ids):
                self.backend.remove_shortcut(shortcut_id)
        self._action_shortcut_ids.clear()
        self.backend.teardown()
        self.next_id = 1
