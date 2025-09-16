import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import shortcuts


def test_windows_backend_registers_hotkey(monkeypatch):
    """Ensure Windows backend registers a hotkey with the native API."""

    monkeypatch.setattr(shortcuts.platform, "system", lambda: "Windows")
    monkeypatch.setattr(shortcuts, "WM_HOTKEY", 0x0312, raising=False)

    register_mock = Mock(return_value=True)
    unregister_mock = Mock(return_value=True)
    user32_mock = SimpleNamespace(
        RegisterHotKey=register_mock, UnregisterHotKey=unregister_mock
    )
    monkeypatch.setattr(
        shortcuts.ctypes,
        "windll",
        SimpleNamespace(user32=user32_mock),
        raising=False,
    )

    backend = shortcuts.WindowsShortcutBackend()

    callback = Mock()
    shortcut_id = 1
    modifiers = ["ctrl", "alt"]
    key = "a"

    assert backend.install_shortcut(modifiers, key, shortcut_id, callback)

    expected_modifiers = sum(
        shortcuts.WindowsShortcutBackend.MODIFIER_MAP[m] for m in modifiers
    )
    expected_key = shortcuts.WindowsShortcutBackend.KEY_MAP[key]
    register_mock.assert_called_once_with(
        None, shortcut_id, expected_modifiers, expected_key
    )

    msg = SimpleNamespace(message=shortcuts.WM_HOTKEY, wParam=shortcut_id)
    assert backend.process_message(msg) is True
    callback.assert_called_once()


class CarbonMock:
    """Lightweight mock for the Carbon framework used on macOS."""

    def __init__(self):
        self.event_target = object()
        self.register_calls = []

        self.GetApplicationEventTarget = self._wrap(lambda: self.event_target)
        self.InstallApplicationEventHandler = self._wrap(lambda *args: 0)
        self.RegisterEventHotKey = self._wrap(self._register_event_hotkey)
        self.UnregisterEventHotKey = self._wrap(lambda *args: 0)
        self.GetEventParameter = self._wrap(self._get_event_parameter)

    def _wrap(self, func):
        def wrapper(*args):
            return func(*args)

        wrapper.argtypes = []
        wrapper.restype = None
        return wrapper

    def _register_event_hotkey(
        self, key, modifiers, hotkey_id_ptr, event_target, options, hotkey_ref_ptr
    ):
        hotkey_ptr = shortcuts.ctypes.cast(
            hotkey_id_ptr,
            shortcuts.ctypes.POINTER(shortcuts.MacShortcutBackend.EventHotKeyID),
        )
        hotkey_id = hotkey_ptr.contents
        self.register_calls.append(
            {
                "key": key,
                "modifiers": modifiers,
                "id": hotkey_id.id,
                "signature": hotkey_id.signature,
                "event_target": event_target,
                "options": options,
            }
        )
        return 0

    def _get_event_parameter(
        self,
        event_ref,
        param_name,
        param_type,
        type_ref,
        size,
        actual_size,
        out_ptr,
    ):
        if self.register_calls:
            hotkey_ptr = shortcuts.ctypes.cast(
                out_ptr,
                shortcuts.ctypes.POINTER(
                    shortcuts.MacShortcutBackend.EventHotKeyID
                ),
            )
            hotkey_ptr.contents.id = self.register_calls[-1]["id"]
        return 0


def test_mac_backend_registers_hotkey(monkeypatch):
    monkeypatch.setattr(shortcuts.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(shortcuts.ctypes.util, "find_library", lambda name: "Carbon")

    carbon = CarbonMock()
    monkeypatch.setattr(shortcuts.ctypes, "CDLL", lambda path: carbon)

    backend = shortcuts.MacShortcutBackend()

    callback = Mock()
    shortcut_id = 2
    modifiers = ["ctrl", "alt"]
    key = "a"

    assert backend.install_shortcut(modifiers, key, shortcut_id, callback)

    assert len(carbon.register_calls) == 1
    register_call = carbon.register_calls[0]
    expected_modifiers = 0
    for mod in modifiers:
        expected_modifiers |= shortcuts.MacShortcutBackend.MODIFIER_MAP[mod]
    expected_key = shortcuts.MacShortcutBackend.KEY_MAP[key]
    assert register_call["key"] == expected_key
    assert register_call["modifiers"] == expected_modifiers
    assert register_call["id"] == shortcut_id
    assert register_call["event_target"] == carbon.event_target

    callback.assert_not_called()
    backend._handle_hotkey(None, object(), None)
    callback.assert_called_once()


class DummyFunction:
    """Callable that records invocations and mimics ctypes function attributes."""

    def __init__(self, func, return_value=None):
        self._func = func
        self._return_value = return_value
        self.calls = []
        self.argtypes = []
        self.restype = None

    def __call__(self, *args):
        self.calls.append(args)
        if self._func is not None:
            return self._func(*args)
        return self._return_value


class XlibMock:
    """Minimal Xlib mock capturing key grabs."""

    def __init__(self):
        self.display = object()
        self.root_window = 42
        self._error_handler = None
        self.grab_calls = []

        self.XOpenDisplay = DummyFunction(lambda arg: self.display)
        self.XDefaultRootWindow = DummyFunction(lambda display: self.root_window)
        self.XStringToKeysym = DummyFunction(self._string_to_keysym)
        self.XKeysymToKeycode = DummyFunction(lambda display, keysym: 38)
        self.XGrabKey = DummyFunction(self._grab_key)
        self.XUngrabKey = DummyFunction(lambda *args: 1)
        self.XFlush = DummyFunction(lambda display: None)
        self.XSync = DummyFunction(lambda display, discard: 0)
        self.XSetErrorHandler = DummyFunction(self._set_error_handler)

    def _string_to_keysym(self, value):
        if value in (b"a", b"A"):
            return 0x0061
        return 0

    def _grab_key(
        self,
        display,
        keycode,
        modifiers,
        root,
        owner_events,
        pointer_mode,
        keyboard_mode,
    ):
        self.grab_calls.append(
            {
                "display": display,
                "keycode": keycode,
                "modifiers": modifiers,
                "root": root,
                "owner_events": owner_events,
                "pointer_mode": pointer_mode,
                "keyboard_mode": keyboard_mode,
            }
        )
        return 1

    def _set_error_handler(self, handler):
        previous = self._error_handler
        self._error_handler = handler
        return previous


def test_linux_backend_registers_hotkey(monkeypatch):
    monkeypatch.setattr(shortcuts.platform, "system", lambda: "Linux")
    monkeypatch.setattr(shortcuts.ctypes.util, "find_library", lambda name: "X11")

    xlib = XlibMock()
    monkeypatch.setattr(shortcuts.ctypes, "CDLL", lambda path: xlib)

    backend = shortcuts.LinuxShortcutBackend()

    callback = Mock()
    shortcut_id = 3
    modifiers = ["ctrl", "alt"]
    key = "a"

    assert backend.install_shortcut(modifiers, key, shortcut_id, callback)

    expected_keycode = 38
    expected_modifiers = 0
    for mod in modifiers:
        expected_modifiers |= shortcuts.LinuxShortcutBackend.MODIFIER_MAP[mod]

    expected_masks = [
        expected_modifiers,
        expected_modifiers | shortcuts.LinuxShortcutBackend.LOCK_MASK,
        expected_modifiers | shortcuts.LinuxShortcutBackend.MOD2_MASK,
        expected_modifiers
        | shortcuts.LinuxShortcutBackend.LOCK_MASK
        | shortcuts.LinuxShortcutBackend.MOD2_MASK,
    ]

    recorded_masks = [call["modifiers"] for call in xlib.grab_calls]
    assert recorded_masks == expected_masks
    assert all(call["keycode"] == expected_keycode for call in xlib.grab_calls)

    backend._handle_key_event(expected_keycode, expected_modifiers)
    callback.assert_called_once()
