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
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtMultimedia import QSound
from PyQt5.QtGui import QCursor, QIcon, QPixmap, QPainter, QColor, QImage, QPen
import mss
from PIL import Image
from google import genai
from pathlib import Path
from shortcuts import ShortcutManager  # Import from new module

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
        self.shortcut_manager = ShortcutManager(self.app)
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
