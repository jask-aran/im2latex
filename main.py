import sys
import os
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
from PyQt5.QtCore import Qt, QRect, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtMultimedia import QSound
from PyQt5.QtGui import QCursor, QIcon, QPixmap, QPainter, QColor, QImage, QPen
import mss
from PIL import Image
from google import genai
from pathlib import Path

from shortcuts import ShortcutManager
from storage import StorageManager
from gui import HistoryWindow

ICON_NORMAL = "assets/scissor.png"
ICON_LOADING = "assets/sand-clock.png"
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "[MASKED_API_KEY]",
    "prompts": {
        "math2latex": "Convert the mathematical content in this image to raw LaTeX math code. Use \\text{} for plain text within equations. For one equation, return only its code. For multiple equations, use \\begin{array}{l}...\\end{array} with \\\\ between equations, matching the image's visual structure. Never use standalone environments like equation or align, and never wrap output in code block markers (e.g., ```). Return NA if no math is present.",
        "text_extraction": "Extract all text from this image and return it as plain text.",
    },
    "shortcuts": {
        "windows": [
            {"shortcut_str": "ctrl+shift+z", "action": "math2latex"},
            {"shortcut_str": "ctrl+shift+x", "action": "text_extraction"},
        ]
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

        # Define CustomRubberBand as an inner class
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


class ApiWorker(QObject):
    finished = pyqtSignal(str, str, Image.Image)  # response_text, action, image
    error = pyqtSignal(str)

    def __init__(self, client, prompt_text, action, image):
        super().__init__()
        self.client = client
        self.prompt_text = prompt_text
        self.action = action
        self.image = image

    @pyqtSlot()
    def process(self):
        """Process the API request in a separate thread."""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=[self.prompt_text, self.image]
            )
            response_text = response.text
            if not response_text:  # Check for empty or None response
                raise ValueError("API returned an empty or invalid response")
            self.finished.emit(response_text, self.action, self.image)
        except Exception as e:
            self.error.emit(str(e))


class Im2LatexApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.screenshot_window = None
        self.history_window = None
        self.config_manager = ConfigManager("config.json", DEFAULT_CONFIG)
        self.client = genai.Client(api_key=self.config_manager.get_api_key())
        all_shortcuts = self.config_manager.get_all_shortcuts()
        self.shortcut_manager = ShortcutManager(
            self.app, all_shortcuts, self.run_pipeline
        )
        self.app.aboutToQuit.connect(self.cleanup)
        self.storage_manager = StorageManager()

        self.virtual_rect = QRect()
        for screen in self.app.screens():
            self.virtual_rect = self.virtual_rect.united(screen.geometry())
        self.monitor_geometry = {
            "top": self.virtual_rect.top(),
            "left": self.virtual_rect.left(),
            "width": self.virtual_rect.width(),
            "height": self.virtual_rect.height(),
        }

        self.tray_icon = QSystemTrayIcon(QIcon("assets/scissor.png"), self.app)
        self.tray_icon.setToolTip("Im2Latex")
        menu = QMenu()
        menu.addAction(QAction("Open GUI", self.app, triggered=self.show_history))
        menu.addAction(QAction("Open Folder", self.app, triggered=self.open_folder))
        menu.addAction(QAction("Print History", self.app, triggered=self.print_history))
        menu.addAction(QAction("Reset History", self.app, triggered=self.reset_history))
        menu.addAction(QAction("Exit", self.app, triggered=self.app.quit))
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

        # Thread management
        self.thread = None
        self.worker = None
        self.api_in_progress = False

    def cleanup(self):
        """Clean up all resources before quitting."""
        self.shortcut_manager.cleanup()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def run_pipeline(self, action):
        def handle_screenshot(pil_image):
            self.tray_icon.setIcon(QIcon(resource_path("assets/sand-clock.png")))

            try:
                prompt_text = self.config_manager.get_prompt(action)
                if not prompt_text:
                    raise ValueError(f"No prompt defined for action: {action}")

                print(f"Sending to API with action: {action}")

                # Start API request in a separate thread
                self.api_in_progress = True
                self.send_to_api_async(pil_image, prompt_text, action)

            except Exception as e:
                print(f"Pipeline error: {e}")
                self.tray_icon.setIcon(QIcon(resource_path("assets/scissor.png")))
                self.api_in_progress = False

        if self.api_in_progress:
            print("API Request already in progress")
            return

        self.screenshot_window = ScreenshotApp(
            handle_screenshot, self.monitor_geometry, self.virtual_rect
        )
        self.screenshot_window.show()
        self.screenshot_window.activateWindow()
        self.screenshot_window.setFocus()

    def send_to_api_async(self, pil_image, prompt_text, action):
        """Send the image to the API asynchronously using a worker thread."""

        # Create a new thread and worker for this API request
        self.thread = QThread()
        self.worker = ApiWorker(self.client, prompt_text, action, pil_image)
        # Move the worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self.handle_api_response)
        self.worker.error.connect(self.handle_api_error)
        self.worker.finished.connect(self.cleanup_thread)
        self.worker.error.connect(self.cleanup_thread)
        self.thread.start()

    def handle_api_response(self, response_text, action, pil_image):
        """Handle the API response from the worker thread."""
        try:
            print(f"API response received: \n```\n{response_text}\n```")
            self.process_response(response_text, action, pil_image)
            print("Response processed and copied to clipboard\n")
        except Exception as e:
            print(f"Error processing API response: {e}")
        finally:
            self.tray_icon.setIcon(QIcon(resource_path("assets/scissor.png")))
            self.api_in_progress = False

    def handle_api_error(self, error_message):
        """Handle errors from the worker thread."""
        print(f"API error while processing {self.worker.action}: {error_message}")
        self.tray_icon.setIcon(QIcon(resource_path("assets/scissor.png")))
        self.api_in_progress = False

    def cleanup_thread(self):
        """Clean up the thread after the worker has finished."""
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None

    def process_response(self, response_text, action, pil_image):
        raw_response = response_text.strip()
        if raw_response.startswith("```latex") or raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[-1].rsplit("\n", 1)[0]
        raw_response = raw_response.strip()

        clipboard = self.app.clipboard()
        clipboard.setText("\n".join(raw_response.splitlines()))

        QSound.play(resource_path("assets/beep.wav"))

        self.storage_manager.save_entry(
            pil_image, self.config_manager.get_prompt(action), raw_response, action
        )

    def show_history(self):
        if self.history_window is None or not self.history_window.isVisible():
            self.history_window = HistoryWindow(self.storage_manager)
            self.history_window.show()
        else:
            self.history_window.raise_()  # Bring to front if already open
            self.history_window.activateWindow()

    def open_folder(self):
        os.startfile(os.getcwd())

    def print_history(self):
        self.storage_manager.print_entries()

    def reset_history(self):
        self.storage_manager.reset_db()

    def run(self):
        sys.exit(self.app.exec_())


def main():
    app = Im2LatexApp()
    app.run()


if __name__ == "__main__":
    main()
