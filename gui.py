import os
import sys

# Use sys.argv approach for dark mode
sys.argv += ["-platform", "windows:darkmode=2"]

from datetime import datetime
from functools import partial
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QTextEdit,
    QScrollArea,
    QPushButton,
    QFileDialog,
    QApplication,
)
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PIL import Image

# Enable high DPI scaling before creating QApplication
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Theme definitions
THEMES = {
    "dark": {
        "main_window": "background-color: #1e1e1e;",
        "central_widget": "background-color: #1e1e1e;",
        "header": "font-size: 22px; font-weight: bold; color: #e0e0e0; margin-bottom: 10px;",
        "history_container": "background-color: #1e1e1e;",
        "scroll_area": "border: none; background-color: #1e1e1e;",
        "scroll_bar": "width: 0px; height: 0px; background: transparent;",
        "frame": "background-color: #333333; border-radius: 6px; border: 1px solid #333333;",
        "timestamp_label": "font-weight: bold; color: #e0e0e0;",
        "action_label": "color: #b0b0b0; font-style: italic;",
        "copy_button": "background-color: #4a90e2; color: #ffffff; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
        "copy_button_hover": "background-color: #357abd;",
        "save_button": "background-color: #2ecc71; color: #ffffff; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
        "save_button_hover": "background-color: #27ae60;",
        "line": "background-color: #333333;",
        "image_label": "background-color: #333333; border: 1px solid #333333;",
        "response_text": "background-color: #333333; border: 1px solid #333333; border-radius: 4px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 16px; color: #e0e0e0;",
        "no_history_label": "font-size: 16px; color: #b0b0b0; padding: 50px;",
        "overlay_background": "#1e1e1e",
        "overlay_fill": QColor(30, 30, 30, 150),  # Less opaque overlay
    },
    "light": {
        "main_window": "background-color: #f5f5f5;",
        "central_widget": "background-color: #f5f5f5;",
        "header": "font-size: 22px; font-weight: bold; color: #333; margin-bottom: 10px;",
        "history_container": "background-color: #f5f5f5;",
        "scroll_area": "border: none; background-color: white;",
        "scroll_bar": "width: 0px; height: 0px; background: transparent;",
        "frame": "background-color: white; border-radius: 6px; border: 1px solid #ddd;",
        "timestamp_label": "font-weight: bold; color: #333;",
        "action_label": "color: #666; font-style: italic;",
        "copy_button": "background-color: #5c85d6; color: white; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
        "copy_button_hover": "background-color: #3a70d6;",
        "save_button": "background-color: #5cb85c; color: white; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
        "save_button_hover": "background-color: #4cae4c;",
        "line": "background-color: #ddd;",
        "image_label": "background-color: #f0f0f0; border: 1px solid #ddd;",
        "response_text": "background-color: #f8f8f8; border: 1px solid #ddd; border-radius: 4px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 16px; color: #333;",
        "no_history_label": "font-size: 16px; color: #888; padding: 50px;",
        "overlay_background": "transparent",
        "overlay_fill": QColor(0, 0, 0, 130),  # Less opaque overlay
    },
}


class OverlayWidget(QWidget):
    def __init__(self, pixmap, parent=None, theme="dark"):
        super().__init__(parent)
        self.pixmap = pixmap
        self.theme = theme
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"background-color: {THEMES[theme]['overlay_background']};")
        self.init_ui()
        if parent:
            self.parent().installEventFilter(self)

    def init_ui(self):
        self.setGeometry(self.parent().rect())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.update_pixmap()
        layout.addWidget(self.image_label)

    def update_pixmap(self):
        if not self.pixmap or self.pixmap.isNull():
            return
        parent_size = self.parent().size()
        max_width = int(parent_size.width() * 0.8)
        max_height = int(parent_size.height() * 0.8)
        scaled_pixmap = self.pixmap.scaled(
            max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), THEMES[self.theme]["overlay_fill"])

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
            self.update_pixmap()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def set_theme(self, theme):
        self.theme = theme
        self.setStyleSheet(f"background-color: {THEMES[theme]['overlay_background']};")
        self.update()


class HistoryItem(QWidget):
    def __init__(self, entry, parent=None, theme="dark"):
        super().__init__(parent)
        self.theme = theme
        (
            self.id,
            self.timestamp,
            self.image_path,
            _,
            self.raw_response,
            self.action,
            _,
        ) = entry
        self.pixmap = None
        self.setMaximumHeight(300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self._setup_header(layout)
        self._setup_content(layout)

    def _setup_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)

        try:
            dt = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
            formatted_time = dt.strftime("%b %d, %Y - %I:%M:%S %p")
        except ValueError:
            formatted_time = self.timestamp

        timestamp_label = QLabel(formatted_time)
        timestamp_label.setStyleSheet(THEMES[self.theme]["timestamp_label"])
        timestamp_label.setFixedHeight(20)

        action_label = QLabel(self.action)
        action_label.setStyleSheet(THEMES[self.theme]["action_label"])
        action_label.setFixedHeight(20)

        self.copy_button = QPushButton("Copy")
        self.copy_button.setStyleSheet(THEMES[self.theme]["copy_button"])
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setFixedSize(60, 20)

        save_image_button = QPushButton("Save")
        save_image_button.setStyleSheet(THEMES[self.theme]["save_button"])
        save_image_button.clicked.connect(self.save_image)
        save_image_button.setFixedSize(60, 20)

        header_layout.addWidget(timestamp_label)
        header_layout.addStretch()
        header_layout.addWidget(action_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.copy_button)
        header_layout.addWidget(save_image_button)

        layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(THEMES[self.theme]["line"])
        layout.addWidget(line)

    def _setup_content(self, layout):
        content_layout = QHBoxLayout()

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setMaximumSize(400, 200)
        self.image_label.setStyleSheet(THEMES[self.theme]["image_label"])
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.show_image_overlay
        self._load_image()

        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setText(self.raw_response)
        self.response_text.setLineWrapMode(QTextEdit.FixedColumnWidth)
        self.response_text.setLineWrapColumnOrWidth(100)
        self.response_text.setStyleSheet(THEMES[self.theme]["response_text"])
        self.response_text.setMaximumHeight(200)

        content_layout.addWidget(self.image_label, 2)
        content_layout.addWidget(self.response_text, 3)
        layout.addLayout(content_layout)
        layout.addStretch()

    def _load_image(self):
        try:
            img = Image.open(self.image_path)
            img_width, img_height = img.size
            max_width, max_height = 400, 200
            scale_factor = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            if img.mode == "RGB":
                qimage = QImage(
                    img.tobytes(),
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format_RGB888,
                )
            else:
                qimage = QImage(
                    img.tobytes(),
                    img.width,
                    img.height,
                    img.width * 4,
                    QImage.Format_RGBA8888,
                )

            self.pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(self.pixmap)
        except Exception as e:
            self.image_label.setText(f"Error loading image: {e}")

    def show_image_overlay(self, event):
        if self.pixmap:
            overlay = OverlayWidget(self.pixmap, self.window(), self.theme)
            overlay.show()

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.raw_response)
        original_text = self.copy_button.text()
        original_style = self.copy_button.styleSheet()
        self.copy_button.setText("Copied!")
        self.copy_button.setStyleSheet(
            f"background-color: {THEMES[self.theme]['copy_button_hover']}; color: #ffffff; "
            f"border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;"
        )
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
        QTimer.singleShot(1500, lambda: self.copy_button.setStyleSheet(original_style))

    def save_image(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Image",
                f"image_{self.id}_{self.timestamp}.png",
                "Images (*.png *.jpg)",
            )
            if filename:
                img = Image.open(self.image_path)
                img.save(filename)
        except Exception as e:
            print(f"Error saving image: {e}")

    def set_theme(self, theme):
        self.theme = theme
        self.image_label.setStyleSheet(THEMES[theme]["image_label"])
        self.response_text.setStyleSheet(THEMES[theme]["response_text"])
        self.copy_button.setStyleSheet(THEMES[theme]["copy_button"])

        # Find frame and labels
        for child in self.findChildren(QFrame):
            child.setStyleSheet(THEMES[theme]["line"])

        # Update labels
        for child in self.findChildren(QLabel):
            if child != self.image_label:
                if "timestamp" in child.text():
                    child.setStyleSheet(THEMES[theme]["timestamp_label"])
                else:
                    child.setStyleSheet(THEMES[theme]["action_label"])


class MainWindow(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self, storage_manager):
        super().__init__()
        self.storage_manager = storage_manager
        self.entries = []
        self.current_theme = "dark"
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        self.setWindowTitle("Im2Latex")
        self.setGeometry(100, 100, 1200, 800)
        self.setMaximumWidth(1500)

        # Set window icon - try both ico and png formats
        icon_path = resource_path("assets/scissor.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            # Force Windows to use the icon for taskbar
            import ctypes

            app_id = "im2latex.app"  # Arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        else:
            icon_path = resource_path("assets/scissor.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(THEMES[self.current_theme]["main_window"])

        central_widget = QWidget()
        central_widget.setStyleSheet(THEMES[self.current_theme]["central_widget"])
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(50, 15, 50, 15)

        # Header with theme toggle
        header_layout = QHBoxLayout()
        header = QLabel("Im2Latex History")
        header.setStyleSheet(THEMES[self.current_theme]["header"])
        self.theme_button = QPushButton(
            "Switch to Light" if self.current_theme == "dark" else "Switch to Dark"
        )
        self.theme_button.setStyleSheet(
            "QPushButton { background-color: #4a90e2; color: #ffffff; border: none; padding: 5px 10px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #357abd; }"
        )
        self.theme_button.clicked.connect(self.toggle_theme)
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_button)
        main_layout.addLayout(header_layout)

        self.history_container = QWidget()
        self.history_container.setStyleSheet(
            THEMES[self.current_theme]["history_container"]
        )
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(20)

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{ {THEMES[self.current_theme]["scroll_area"]} }}
            QScrollBar:vertical, QScrollBar:horizontal {{ {THEMES[self.current_theme]["scroll_bar"]} }}
            """
        )
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.history_container)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area)

        self.load_history()
        self.refresh_signal.connect(self.load_history)

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(2000)

    def check_for_updates(self):
        current_entries = self.storage_manager.get_all_entries()
        if len(current_entries) != len(self.entries):
            self.refresh_signal.emit()

    def load_history(self):
        # Clear existing widgets
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.entries = self.storage_manager.get_all_entries()
        if not self.entries:
            no_history_label = QLabel(
                "No history entries found. Take some screenshots!"
            )
            no_history_label.setAlignment(Qt.AlignCenter)
            no_history_label.setStyleSheet(
                THEMES[self.current_theme]["no_history_label"]
            )
            self.history_layout.addWidget(no_history_label)
            return

        for entry in self.entries:
            history_item = HistoryItem(entry, theme=self.current_theme)
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.StyledPanel)
            item_frame.setStyleSheet(THEMES[self.current_theme]["frame"])
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.addWidget(history_item)
            self.history_layout.addWidget(item_frame)

        self.history_layout.addStretch()

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme_button.setText(
            "Switch to Light" if self.current_theme == "dark" else "Switch to Dark"
        )
        self.setStyleSheet(THEMES[self.current_theme]["main_window"])
        self.centralWidget().setStyleSheet(THEMES[self.current_theme]["central_widget"])

        # Update header style
        for header in self.findChildren(QLabel):
            if header.text() == "Im2Latex History":
                header.setStyleSheet(THEMES[self.current_theme]["header"])
                break

        self.history_container.setStyleSheet(
            THEMES[self.current_theme]["history_container"]
        )

        # Update scrollarea style
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scroll_area.setStyleSheet(
                f"""
                QScrollArea {{ {THEMES[self.current_theme]["scroll_area"]} }}
                QScrollBar:vertical, QScrollBar:horizontal {{ {THEMES[self.current_theme]["scroll_bar"]} }}
                """
            )

        self.load_history()  # Reload history to apply new theme to items


if __name__ == "__main__":
    from storage import StorageManager

    app = QApplication(sys.argv)
    storage = StorageManager("history.db")
    window = MainWindow(storage)
    window.show()
    sys.exit(app.exec_())
