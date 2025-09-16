import sys
import os
import json
import time

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QSound
import mss
from PIL import Image
from pathlib import Path

from shortcuts import ShortcutManager
from storage import StorageManager
from gui import MainWindow
from chat_gui import ChatApp
from api_manager import ApiManager, ChatApiManager

ICON_NORMAL = "assets/scissor.png"
ICON_LOADING = "assets/sand-clock.png"
SOUND_DONE = "assets/beep.wav"
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "YOUR_API_KEY_HERE",
    "prompts": {
        "math2latex": "Convert the mathematical content in this image to raw LaTeX math code. Use \\text{} for plain text within equations. For one equation, return only its code. For multiple equations, use \\begin{array}{l}...\\end{array} with \\\\ between equations, matching the image’s visual structure. Never use standalone environments like equation or align, and never wrap output in code block markers (e.g., ```). Return NA if no math is present.",
        "text_extraction": "Extract all text from this image and return it as plain text.",
        "table": "Convert the information in the image to a latex formatted table. Use a hbar and bolding for the header row where appropriate, and only return the necessary lines for posting into an existing document. Add an empty caption to add a table number but do not fill it unless there is a title visible in the image.",
        "chem2smiles": "Convert the chemical structure or formula in this image to SMILES notation. Pay really close attention to the chemical structure to ensure you have matched it perfectly. Return 'NA' if no chemical structure or formula is present or recognizable. Do not return anything but the SMILES code itself.",
    },
    "shortcuts": {
        "windows": [
            {"shortcut_str": "ctrl+alt+z", "action": "math2latex"},
            {"shortcut_str": "ctrl+alt+x", "action": "text_extraction"},
            {"shortcut_str": "ctrl+alt+c", "action": "table"},
            {"shortcut_str": "ctrl+alt+s", "action": "chem2smiles"},
        ],
        "darwin": [
            {"shortcut_str": "ctrl+alt+z", "action": "math2latex"},
            {"shortcut_str": "ctrl+alt+x", "action": "text_extraction"},
            {"shortcut_str": "ctrl+alt+c", "action": "table"},
            {"shortcut_str": "ctrl+alt+s", "action": "chem2smiles"},
        ],
        "linux": [
            {"shortcut_str": "ctrl+alt+z", "action": "math2latex"},
            {"shortcut_str": "ctrl+alt+x", "action": "text_extraction"},
            {"shortcut_str": "ctrl+alt+c", "action": "table"},
            {"shortcut_str": "ctrl+alt+s", "action": "chem2smiles"},
        ],
    },
}
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class ConfigManager:
    def __init__(self, file_path, default_config):
        self.file_path = Path(file_path)
        self.default_config = default_config
        self.config = self.load_or_create()

    def load_or_create(self):
        try:
            config = json.loads(self.file_path.read_text())
            if not isinstance(config, dict) or not config.get("api_key", "").strip():
                raise ValueError("Invalid or missing API key")
            if "prompts" not in config or not config["prompts"]:
                raise ValueError("No prompts defined")
            return config
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            self.file_path.write_text(json.dumps(self.default_config, indent=4))
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Im2Latex Config Error")
            msg_box.setText(
                f"Config error: {e}. A new default config has been created. Please edit it with a valid API key."
            )
            open_folder_button = msg_box.addButton(
                "Open Installation Folder", QMessageBox.ActionRole
            )
            msg_box.addButton(QMessageBox.Ok)
            msg_box.exec_()
            if msg_box.clickedButton() == open_folder_button:
                os.startfile(os.getcwd())
            sys.exit(1)

    def get_config(self):
        return self.config

    def get_all_shortcuts(self):
        return self.config.get("shortcuts", {})

    def get_api_key(self):
        return self.config.get("api_key", "")

    def get_prompt(self, action):
        """Retrieve the prompt text for a given action."""
        return self.config.get("prompts", {}).get(action, "")


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

        class CustomRubberBand(QRubberBand):
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setPen(QPen(QColor(255, 255, 255), 2))  # White border, 2px
                painter.setBrush(QColor(255, 255, 255, 50))  # White fill, 50% opacity
                painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        self.rubberBand = CustomRubberBand(QRubberBand.Rectangle, self)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.image, event.rect())
        painter.setBrush(QColor(0, 0, 0, 100))
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
            self.callback(pil_image)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("Escape key pressed, closing screenshot window")
            self.close()



class Im2LatexApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.screenshot_window = None
        self.main_gui = None
        self.chat_window = None
        self.app.aboutToQuit.connect(self.cleanup)

        self.config_manager = ConfigManager("config.json", DEFAULT_CONFIG)
        self.api_manager = ApiManager(self.config_manager.get_api_key())
        self.api_manager.api_response_ready.connect(self.process_response)
        self.api_manager.api_error.connect(self.handle_api_error)
        self.chat_manager = ChatApiManager(self.config_manager.get_api_key())

        all_shortcuts = self.config_manager.get_all_shortcuts()
        self.shortcut_manager = ShortcutManager(
            self.app, all_shortcuts, self.run_pipeline
        )

        self.storage_manager = StorageManager()

        # Use mss to get the actual screen geometry instead of Qt
        with mss.mss() as sct:
            # Get all monitors and find the bounding box
            monitors = sct.monitors[1:]  # Skip the "All in One" monitor (index 0)
            if monitors:
                # Calculate the bounding box of all monitors
                left = min(m["left"] for m in monitors)
                top = min(m["top"] for m in monitors)
                right = max(m["left"] + m["width"] for m in monitors)
                bottom = max(m["top"] + m["height"] for m in monitors)
                
                self.monitor_geometry = {
                    "top": top,
                    "left": left,
                    "width": right - left,
                    "height": bottom - top,
                }
                self.virtual_rect = QRect(left, top, right - left, bottom - top)
            else:
                # Fallback to primary monitor
                primary = sct.monitors[0]
                self.monitor_geometry = primary
                self.virtual_rect = QRect(
                    primary["left"], primary["top"], 
                    primary["width"], primary["height"]
                )

        self.tray_icon = QSystemTrayIcon(QIcon(resource_path(ICON_NORMAL)), self.app)
        self.tray_icon.setToolTip("Im2Latex")
        self.tray_icon.activated.connect(
            lambda reason: (
                self.show_gui() if reason != QSystemTrayIcon.Context else None
            )
        )
        menu = QMenu()
        menu.addAction(QAction("Open GUI", self.app, triggered=self.show_gui))
        menu.addAction(QAction("Open Folder", self.app, triggered=self.open_folder))
        menu.addAction(QAction("Print History", self.app, triggered=self.print_history))
        menu.addAction(QAction("Reset History", self.app, triggered=self.reset_history))
        menu.addAction(QAction("Show Chat", self.app, triggered=self.show_chat))
        menu.addAction(QAction("Exit", self.app, triggered=self.app.quit))
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def cleanup(self):
        self.shortcut_manager.cleanup()
        self.api_manager.cleanup()
        self.chat_manager.cleanup()

    def run_pipeline(self, action):
        if self.api_manager.api_in_progress:
            print("API Request already in progress")
            return

        # Check for prompt early, before proceeding to screenshot
        prompt_text = self.config_manager.get_prompt(action)
        if not prompt_text:
            print(f"No prompt defined for action: {action}")
            return  # Early exit before creating the screenshot window

        def handle_screenshot(pil_image):
            try:
                print(f"Sending to API with action: {action}")
                self.tray_icon.setIcon(QIcon(resource_path(ICON_LOADING)))
                self.api_start_time = time.time()
                self.api_manager.send_request(pil_image, prompt_text, action)
            except Exception as e:
                print(f"Pipeline error: {e}")
                self.tray_icon.setIcon(QIcon(resource_path(ICON_NORMAL)))

        self.screenshot_window = ScreenshotApp(
            handle_screenshot, self.monitor_geometry, self.virtual_rect
        )
        self.screenshot_window.show()
        self.screenshot_window.activateWindow()
        self.screenshot_window.setFocus()

    def process_response(self, response_text, action, pil_image):
        # print(f"API response received: \n```\n{response_text}\n```")
        end_time = time.time()
        elapsed_time = (
            end_time - self.api_start_time if hasattr(self, "api_start_time") else 0
        )
        print(
            f"API response received in {elapsed_time:.2f} seconds: \n```\n{response_text}\n```"
        )

        clipboard = self.app.clipboard()
        clipboard.setText("\n".join(response_text.splitlines()))

        QSound.play(resource_path(SOUND_DONE))

        self.storage_manager.save_entry(
            pil_image, self.config_manager.get_prompt(action), response_text, action
        )
        print("Response processed and copied to clipboard\n")

        self.tray_icon.setIcon(QIcon(resource_path(ICON_NORMAL)))

    def handle_api_error(self, error_message):
        print(f"API error: {error_message}")
        self.tray_icon.setIcon(QIcon(resource_path(ICON_NORMAL)))

    def show_gui(self):
        if self.main_gui is None or not self.main_gui.isVisible():
            self.main_gui = MainWindow(self.storage_manager)
            self.main_gui.show()
        else:
            self.main_gui.raise_()
            self.main_gui.activateWindow()

    def show_chat(self):
        if self.chat_window is None:
            self.chat_window = ChatApp(self.chat_manager)
            self.chat_window.destroyed.connect(self._chat_window_destroyed)

        if not self.chat_window.isVisible():
            self.chat_window.show()
        else:
            self.chat_window.raise_()
            self.chat_window.activateWindow()

        self.chat_window.setFocus()

    def _chat_window_destroyed(self, _=None):
        self.chat_window = None

    def open_folder(self):
        os.startfile(os.getcwd())

    def print_history(self):
        self.storage_manager.print_entries()

    def reset_history(self):
        self.storage_manager.reset_db()

    def run(self):
        sys.exit(self.app.exec_())


def main():
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
    app = Im2LatexApp()
    app.run()


if __name__ == "__main__":
    main()
