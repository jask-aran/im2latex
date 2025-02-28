import sys
import os
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
from PyQt5.QtMultimedia import QSound  # Added for sound
from PyQt5.QtGui import QClipboard, QCursor, QIcon
import mss
import mss.tools
from PIL import Image
from io import BytesIO
import requests

from google import genai

# Constants for Windows hotkey registration
MOD_WIN = 0x0008
MOD_SHIFT = 0x0004
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002

# Global reference for the screenshot window
active_screenshot_window = None

# Config file settings
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "YOUR_API_KEY_HERE",
    "prompt": "Convert the mathematical content in this image to raw LaTeX math code. Use \\text{} for plain text within equations. For one equation, return only its code. For multiple equations, use \\begin{array}{l}...\\end{array} with \\\\ between equations, matching the image’s visual structure. Never use standalone environments like equation or align, and never wrap output in code block markers (e.g., ```). Return NA if no math is present.",
}


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_or_create_config(app):
    """Load config file or create it if it doesn't exist, exit on API key failure."""
    try:
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            QMessageBox.critical(
                None,
                "Im2Latex Warning",
                f"Created new config file at {CONFIG_FILE}. Please edit it with your API key.",
            )
            sys.exit(1)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        # Validate API key and exit if invalid
        if (
            "api_key" not in config
            or not config["api_key"]
            or config["api_key"] == "YOUR_API_KEY_HERE"
        ):
            QMessageBox.critical(
                None, "Im2Latex Error", f"Please set a valid API key in {CONFIG_FILE}"
            )
            sys.exit(1)

        # Handle prompt - use default if missing or empty
        if "prompt" not in config or not config["prompt"]:
            config["prompt"] = DEFAULT_CONFIG["prompt"]
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            QMessageBox.information(
                None,
                "Im2Latex Info",
                f"No prompt found in {CONFIG_FILE}. Using default prompt and updating config file.",
            )

        return config
    except json.JSONDecodeError:
        QMessageBox.critical(
            None,
            "Im2Latex Error",
            f"{CONFIG_FILE} is invalid JSON. Please fix or delete it to create a new one.",
        )
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(
            None, "Im2Latex Error", f"Error accessing config file: {e}"
        )
        sys.exit(1)


# Initialize globals from config (will be set after app creation)
client = None
prompt_text = None


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback, hotkey_id=1, modifiers=MOD_WIN | MOD_SHIFT, vk=0x5A):
        super().__init__()
        self.callback = callback
        self.hotkey_id = hotkey_id
        self.user32 = ctypes.windll.user32

        if not self.user32.RegisterHotKey(None, self.hotkey_id, modifiers, vk):
            print("Failed to register hotkey. It might already be in use.")
        else:
            print("Hotkey registered.")

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(
                ctypes.c_void_p(int(message)), ctypes.POINTER(wintypes.MSG)
            ).contents
            if msg.message == WM_HOTKEY and msg.wParam == self.hotkey_id:
                self.callback()
                return True, 0
        return False, 0

    def unregister(self):
        self.user32.UnregisterHotKey(None, self.hotkey_id)


class ScreenshotApp(QMainWindow):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowTitle("Select Area for Screenshot")
        self.setWindowOpacity(0.2)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(QCursor(Qt.CrossCursor))

        virtual_rect = QRect()
        for screen in QApplication.screens():
            virtual_rect = virtual_rect.united(screen.geometry())
        self.setGeometry(virtual_rect)

        self.origin = None
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)

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
            pil_image = self.capture_screenshot(rect)
            self.callback(pil_image)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def capture_screenshot(self, rect):
        global_top_left = self.mapToGlobal(rect.topLeft())
        monitor = {
            "top": global_top_left.y(),
            "left": global_top_left.x(),
            "width": rect.width(),
            "height": rect.height(),
        }
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            try:
                pil_image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                return pil_image
            except Exception as e:
                print(f"Failed to capture screenshot: {e}")
                return None


def trigger_screenshot():
    if not client:
        QMessageBox.critical(
            None, "Im2Latex Error", "Cannot take screenshot: No valid API configuration"
        )
        return
    global active_screenshot_window
    active_screenshot_window = ScreenshotApp(process_screenshot)
    active_screenshot_window.show()


def process_screenshot(pil_image):
    response_text = send_to_api(pil_image)
    if response_text:
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(response_text.splitlines()))
        print("Response copied to clipboard")
        QSound.play(resource_path("assets/beep.wav"))  # Play soft tone


def send_to_api(pil_image):
    if pil_image is None:
        print("No image to send to API")
        return None

    if not client:
        QMessageBox.critical(
            None,
            "Im2Latex Error",
            "API client not initialized due to configuration error",
        )
        return None

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt_text,
                pil_image,
            ],
        )
        raw_response = response.text.strip()
        if raw_response.startswith("```latex") or raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[-1]
            raw_response = raw_response.rsplit("\n", 1)[0]
        raw_response = raw_response.strip()
        print(f"API response: {raw_response}")
        return raw_response
    except Exception as e:
        print(f"Failed to send to API: {e}")
        return None


def open_folder():
    os.startfile(os.getcwd())


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load config and initialize globals
    global client, prompt_text
    config = load_or_create_config(app)
    client = genai.Client(api_key=config["api_key"])
    prompt_text = config["prompt"]

    tray_icon = QSystemTrayIcon(QIcon(resource_path("assets/scissor.png")), parent=app)
    tray_icon.setToolTip("Im2Latex")
    menu = QMenu()

    open_folder_action = QAction("Open Folder")
    open_folder_action.triggered.connect(open_folder)
    menu.addAction(open_folder_action)

    exit_action = QAction("Exit")
    exit_action.triggered.connect(app.quit)
    menu.addAction(exit_action)

    tray_icon.setContextMenu(menu)
    tray_icon.show()

    hotkey_filter = GlobalHotkeyFilter(trigger_screenshot)
    app.installNativeEventFilter(hotkey_filter)
    app.aboutToQuit.connect(lambda: hotkey_filter.unregister())

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
