import sys
import os
import platform
import ctypes
import ctypes.wintypes as wintypes
import json
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QRubberBand,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QRect, QAbstractNativeEventFilter
from PyQt5.QtMultimedia import QSound
from PyQt5.QtGui import QCursor, QIcon, QPixmap, QPainter, QColor, QImage, QPen
import mss
from PIL import Image
from google import genai
from pathlib import Path

# Windows constants
WM_HOTKEY = 0x0312

# Config settings
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "YOUR_API_KEY_HERE",
    "prompt": "Convert the mathematical content in this image to raw LaTeX math code. Use \\text{} for plain text within equations. For one equation, return only its code. For multiple equations, use \\begin{array}{l}...\\end{array} with \\\\ between equations, matching the image's visual structure. Never use standalone environments like equation or align, and never wrap output in code block markers (e.g., ```). Return NA if no math is present.",
    "shortcuts": [{"shortcut_str": "win+shift+z", "action": "trigger_screenshot"}],
}

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_config(default_config=DEFAULT_CONFIG):
    config_path = Path(CONFIG_FILE)
    try:
        config = json.loads(config_path.read_text())
        if (
            not isinstance(config, dict)
            or not config.get("api_key", "").strip()
            or config["api_key"] == "YOUR_API_KEY_HERE"
        ):
            raise ValueError("Invalid or missing API key")
        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        config_path.write_text(json.dumps(default_config, indent=4))
        show_config_error(
            f"A new default config has been created. Please edit it with a valid API key."
        )
        sys.exit(1)
    except ValueError as e:
        show_config_error(f"{e}. Please fix the API key in config.json.")
        sys.exit(1)


def show_config_error(message):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Im2Latex Config Error")
    msg_box.setText(message)
    open_folder_button = msg_box.addButton(
        "Open Installation Folder", QMessageBox.ActionRole
    )
    msg_box.addButton(QMessageBox.Ok)
    msg_box.exec_()
    if msg_box.clickedButton() == open_folder_button:
        os.startfile(os.getcwd())


class ShortcutBackend:
    def register_shortcut(self, modifiers, key, shortcut_id, callback):
        raise NotImplementedError

    def unregister_shortcut(self, shortcut_id):
        raise NotImplementedError

    def process_message(self, msg):
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
        self.shortcuts = {}  # {shortcut_id: callback}

    def register_shortcut(self, modifiers, key, shortcut_id, callback):
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

    def unregister_shortcut(self, shortcut_id):
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


def get_shortcut_backend():
    if platform.system() == "Windows":
        return WindowsShortcutBackend()
    raise NotImplementedError(f"Unsupported platform: {platform.system()}")


class ShortcutManager:
    def __init__(self):
        self.backend = get_shortcut_backend()
        self.next_id = 1

    def parse_shortcut(self, shortcut_str):
        parts = shortcut_str.lower().split("+")
        if not parts:
            raise ValueError(f"Invalid shortcut string: {shortcut_str}")
        modifiers = parts[:-1]
        key = parts[-1]
        return modifiers, key

    def register_shortcut(self, shortcut_str, callback):
        modifiers, key = self.parse_shortcut(shortcut_str)
        shortcut_id = self.next_id
        if self.backend.register_shortcut(modifiers, key, shortcut_id, callback):
            self.next_id += 1
            return shortcut_id
        raise ValueError(f"Failed to register shortcut: {shortcut_str}")

    def unregister_shortcut(self, shortcut_id):
        return self.backend.unregister_shortcut(shortcut_id)

    def process_message(self, msg):
        return self.backend.process_message(msg)

    def cleanup(self):
        self.backend.shortcuts.clear()
        self.next_id = 1


class ShortcutEventFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(
                ctypes.c_void_p(int(message)), ctypes.POINTER(wintypes.MSG)
            ).contents
            if self.manager.process_message(msg):
                return True, 0
        return False, 0


class CustomRubberBand(QRubberBand):
    def __init__(self, shape, parent=None):
        super().__init__(shape, parent)
        self.border_color = QColor(255, 255, 255)
        self.fill_color = QColor(255, 255, 255, 50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(self.border_color, 2))
        painter.setBrush(self.fill_color)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))


class ScreenshotApp(QMainWindow):
    def __init__(self, callback, monitor_geometry, virtual_rect):
        super().__init__()
        self.callback = callback
        self.monitor_geometry = monitor_geometry
        self.screenshot = mss.mss().grab(self.monitor_geometry)
        self.image = QImage(
            self.screenshot.rgb,
            self.screenshot.width,
            self.screenshot.height,
            self.screenshot.width * 3,
            QImage.Format_RGB888,
        )
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setGeometry(virtual_rect)
        self.setWindowOpacity(1.0)
        self.origin = None
        self.rubberBand = CustomRubberBand(QRubberBand.Rectangle, self)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.image, event.rect())
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.drawRect(event.rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, self.origin))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if self.rubberBand.isVisible():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rubberBand.geometry()
            self.close()
            pil_image = Image.frombytes(
                "RGB",
                (self.screenshot.width, self.screenshot.height),
                self.screenshot.rgb,
            ).crop((rect.left(), rect.top(), rect.right(), rect.bottom()))
            pil_image.save(os.path.join(os.getcwd(), "screenshot.png"), "PNG")
            self.callback(pil_image)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("Escape key pressed, closing screenshot window")
            self.close()


class Im2LatexApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.config = load_config()
        self.client = genai.Client(api_key=self.config["api_key"])
        self.prompt_text = self.config["prompt"]
        self.screenshot_window = None

        self.virtual_rect = QRect()
        for screen in self.app.screens():
            self.virtual_rect = self.virtual_rect.united(screen.geometry())

        self.monitor_geometry = {
            "top": self.virtual_rect.top(),
            "left": self.virtual_rect.left(),
            "width": self.virtual_rect.width(),
            "height": self.virtual_rect.height(),
        }

        self.tray_icon = QSystemTrayIcon(
            QIcon(resource_path("assets/scissor.png")), self.app
        )
        self.tray_icon.setToolTip("Im2Latex")
        self.setup_tray_menu()
        self.tray_icon.show()

        # Initialize shortcut manager
        self.shortcut_manager = ShortcutManager()
        self.shortcut_filter = ShortcutEventFilter(self.shortcut_manager)
        self.app.installNativeEventFilter(self.shortcut_filter)
        self.app.aboutToQuit.connect(self.shortcut_manager.cleanup)

        # Callback map for actions defined in config
        self.callback_map = {"trigger_screenshot": self.trigger_screenshot}

        # Load shortcuts from config
        for shortcut in self.config["shortcuts"]:
            try:
                self.shortcut_manager.register_shortcut(
                    shortcut["shortcut_str"], self.callback_map[shortcut["action"]]
                )
                print(f"Shortcut {shortcut['shortcut_str']} registered successfully")
            except ValueError as e:
                print(f"Shortcut registration failed: {e}")

    def setup_tray_menu(self):
        menu = QMenu()
        menu.addAction(QAction("Open Folder", self.app, triggered=self.open_folder))
        menu.addAction(QAction("Exit", self.app, triggered=self.app.quit))
        self.tray_icon.setContextMenu(menu)

    def trigger_screenshot(self):
        self.screenshot_window = ScreenshotApp(
            self.process_screenshot, self.monitor_geometry, self.virtual_rect
        )
        self.screenshot_window.show()
        self.screenshot_window.activateWindow()
        self.screenshot_window.setFocus()

    def process_screenshot(self, pil_image):
        response_text = self.send_to_api(pil_image)
        if response_text:
            clipboard = self.app.clipboard()
            clipboard.setText("\n".join(response_text.splitlines()))
            print("Response copied to clipboard")
            QSound.play(resource_path("assets/beep.wav"))

    def send_to_api(self, pil_image):
        try:
            print("Sending to API")
            self.tray_icon.setIcon(QIcon(resource_path("assets/sand-clock.png")))
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=[self.prompt_text, pil_image]
            )
            raw_response = response.text.strip()
            if raw_response.startswith("```latex") or raw_response.startswith("```"):
                raw_response = raw_response.split("\n", 1)[-1].rsplit("\n", 1)[0]
            raw_response = raw_response.strip()
            print(f"API response: {raw_response}")
            self.tray_icon.setIcon(QIcon(resource_path("assets/scissor.png")))
            return raw_response
        except Exception as e:
            print(f"Failed to send to API: {e}")
            return None

    def open_folder(self):
        os.startfile(os.getcwd())

    def run(self):
        sys.exit(self.app.exec_())


def main():
    app = Im2LatexApp()
    app.run()


if __name__ == "__main__":
    main()
