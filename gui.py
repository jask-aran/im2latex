import os
import sys
from datetime import datetime
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

# Enable high DPI scaling
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    return (
        os.path.join(sys._MEIPASS, relative_path)
        if hasattr(sys, "_MEIPASS")
        else os.path.join(os.path.abspath("."), relative_path)
    )


# Theme definitions
THEMES = {
    "dark": {
        "bg_color": "#1e1e1e",
        "frame_color": "#333333",
        "text_color": "#e0e0e0",
        "secondary_text": "#b0b0b0",
        "copy_btn": {"bg": "#4a90e2", "hover": "#357abd"},
        "save_btn": {"bg": "#2ecc71", "hover": "#27ae60"},
        "overlay_fill": QColor(30, 30, 30, 150),
    },
    "light": {
        "bg_color": "#f5f5f5",
        "frame_color": "white",
        "text_color": "#333",
        "secondary_text": "#666",
        "copy_btn": {"bg": "#5c85d6", "hover": "#3a70d6"},
        "save_btn": {"bg": "#5cb85c", "hover": "#4cae4c"},
        "overlay_fill": QColor(0, 0, 0, 130),
    },
}

# Generate complete styles from theme properties
for theme_name, theme in THEMES.items():
    is_dark = theme_name == "dark"
    theme.update(
        {
            "main_window": f"background-color: {theme['bg_color']};",
            "central_widget": f"background-color: {theme['bg_color']};",
            "header": f"font-size: 22px; font-weight: bold; color: {theme['text_color']}; margin-bottom: 10px;",
            "history_container": f"background-color: {theme['bg_color']};",
            "scroll_area": f"border: none; background-color: {theme['bg_color'] if is_dark else 'white'};",
            "scroll_bar": "width: 0px; height: 0px; background: transparent;",
            "frame": f"background-color: {theme['frame_color']}; border-radius: 6px; border: 1px solid {theme['frame_color'] if is_dark else '#ddd'};",
            "timestamp_label": f"font-weight: bold; color: {theme['text_color']};",
            "action_label": f"color: {theme['secondary_text']}; font-style: italic;",
            "copy_button": f"background-color: {theme['copy_btn']['bg']}; color: #ffffff; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
            "copy_button_hover": f"background-color: {theme['copy_btn']['hover']};",
            "save_button": f"background-color: {theme['save_btn']['bg']}; color: #ffffff; border: none; padding: 2px 5px; border-radius: 3px; font-size: 12px;",
            "save_button_hover": f"background-color: {theme['save_btn']['hover']};",
            "line": f"background-color: {theme['frame_color'] if is_dark else '#ddd'};",
            "image_label": f"background-color: {theme['frame_color'] if is_dark else '#f0f0f0'}; border: 1px solid {theme['frame_color'] if is_dark else '#ddd'};",
            "response_text": f"background-color: {theme['frame_color'] if is_dark else '#f8f8f8'}; border: 1px solid {theme['frame_color'] if is_dark else '#ddd'}; border-radius: 4px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 16px; color: {theme['text_color']};",
            "no_history_label": f"font-size: 16px; color: {theme['secondary_text']}; padding: 50px;",
            "overlay_background": theme["bg_color"] if is_dark else "transparent",
        }
    )


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
        max_width, max_height = int(parent_size.width() * 0.8), int(
            parent_size.height() * 0.8
        )
        self.image_label.setPixmap(
            self.pixmap.scaled(
                max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

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

        # Header section
        header = QHBoxLayout()
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

        save_button = QPushButton("Save")
        save_button.setStyleSheet(THEMES[self.theme]["save_button"])
        save_button.clicked.connect(self.save_image)
        save_button.setFixedSize(60, 20)

        header.addWidget(timestamp_label)
        header.addStretch()
        header.addWidget(action_label)
        header.addSpacing(10)
        header.addWidget(self.copy_button)
        header.addWidget(save_button)
        layout.addLayout(header)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet(THEMES[self.theme]["line"])
        layout.addWidget(divider)

        # Content section
        content = QHBoxLayout()

        # Image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setMaximumSize(400, 200)
        self.image_label.setStyleSheet(THEMES[self.theme]["image_label"])
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.show_image_overlay
        self._load_image()

        # Text
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setText(self.raw_response)
        self.response_text.setLineWrapMode(QTextEdit.FixedColumnWidth)
        self.response_text.setLineWrapColumnOrWidth(100)
        self.response_text.setStyleSheet(THEMES[self.theme]["response_text"])
        self.response_text.setMaximumHeight(200)

        content.addWidget(self.image_label, 2)
        content.addWidget(self.response_text, 3)
        layout.addLayout(content)
        layout.addStretch()

    def _load_image(self):
        try:
            img = Image.open(self.image_path)
            img_width, img_height = img.size
            scale_factor = min(400 / img_width, 200 / img_height)
            new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to QImage based on mode
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
            OverlayWidget(self.pixmap, self.window(), self.theme).show()

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.raw_response)
        original_text, original_style = (
            self.copy_button.text(),
            self.copy_button.styleSheet(),
        )
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
                Image.open(self.image_path).save(filename)
        except Exception as e:
            print(f"Error saving image: {e}")

    def set_theme(self, theme):
        self.theme = theme
        self.image_label.setStyleSheet(THEMES[theme]["image_label"])
        self.response_text.setStyleSheet(THEMES[theme]["response_text"])
        self.copy_button.setStyleSheet(THEMES[theme]["copy_button"])

        for child in self.findChildren(QFrame):
            child.setStyleSheet(THEMES[theme]["line"])

        for child in self.findChildren(QLabel):
            if child != self.image_label:
                style_key = (
                    "timestamp_label" if "timestamp" in child.text() else "action_label"
                )
                child.setStyleSheet(THEMES[theme][style_key])


class MainWindow(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self, storage_manager):
        super().__init__()
        self.storage_manager = storage_manager
        self.entries = []
        self.current_theme = "dark"
        self.init_ui()
        self.set_dark_titlebar()
        self.setup_timer()

    def init_ui(self):
        # Window setup
        self.setWindowTitle("Im2Latex")
        self.setGeometry(100, 100, 1200, 800)
        self.setMaximumWidth(1500)
        self.set_window_icon()
        self.setStyleSheet(THEMES[self.current_theme]["main_window"])

        # Central widget
        central_widget = QWidget()
        central_widget.setStyleSheet(THEMES[self.current_theme]["central_widget"])
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(50, 15, 50, 15)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Im2Latex History")
        header.setStyleSheet(THEMES[self.current_theme]["header"])

        self.theme_button = QPushButton(
            "Switch to Light" if self.current_theme == "dark" else "Switch to Dark"
        )
        self.theme_button.setStyleSheet(
            "QPushButton { background-color: #4a90e2; color: #ffffff; border: none; "
            "padding: 5px 10px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #357abd; }"
        )
        self.theme_button.clicked.connect(self.toggle_theme)

        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_button)
        main_layout.addLayout(header_layout)

        # History container
        self.history_container = QWidget()
        self.history_container.setStyleSheet(
            THEMES[self.current_theme]["history_container"]
        )
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(20)

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(
            f"QScrollArea {{ {THEMES[self.current_theme]['scroll_area']} }}"
            f"QScrollBar:vertical, QScrollBar:horizontal {{ {THEMES[self.current_theme]['scroll_bar']} }}"
        )
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.history_container)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area)

        # Load data
        self.refresh_signal.connect(self.load_history)
        self.load_history()

    def set_window_icon(self):
        for icon_ext in ["ico", "png"]:
            icon_path = resource_path(f"assets/scissor.{icon_ext}")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                if icon_ext == "ico" and sys.platform == "win32":
                    import ctypes

                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                        "im2latex.app"
                    )
                break

    def set_dark_titlebar(self):
        if sys.platform == "win32":
            try:
                from ctypes import windll, c_int, byref, sizeof

                hwnd = int(self.winId())
                darkMode = c_int(1)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, byref(darkMode), sizeof(darkMode)
                )
            except Exception as e:
                print(f"Failed to set dark titlebar: {e}")

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

        # Get entries
        self.entries = self.storage_manager.get_all_entries()

        # Show empty state or history items
        if not self.entries:
            no_history = QLabel("No history entries found. Take some screenshots!")
            no_history.setAlignment(Qt.AlignCenter)
            no_history.setStyleSheet(THEMES[self.current_theme]["no_history_label"])
            self.history_layout.addWidget(no_history)
            return

        # Add history items
        for entry in self.entries:
            # Create wrapped history item
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.StyledPanel)
            item_frame.setStyleSheet(THEMES[self.current_theme]["frame"])

            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.addWidget(HistoryItem(entry, theme=self.current_theme))

            self.history_layout.addWidget(item_frame)

        self.history_layout.addStretch()

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme_button.setText(
            "Switch to Light" if self.current_theme == "dark" else "Switch to Dark"
        )

        # Update styles
        self.setStyleSheet(THEMES[self.current_theme]["main_window"])
        self.centralWidget().setStyleSheet(THEMES[self.current_theme]["central_widget"])

        # Update header
        header = next(
            (h for h in self.findChildren(QLabel) if h.text() == "Im2Latex History"),
            None,
        )
        if header:
            header.setStyleSheet(THEMES[self.current_theme]["header"])

        # Update container and scroll
        self.history_container.setStyleSheet(
            THEMES[self.current_theme]["history_container"]
        )
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scroll_area.setStyleSheet(
                f"QScrollArea {{ {THEMES[self.current_theme]['scroll_area']} }}"
                f"QScrollBar:vertical, QScrollBar:horizontal {{ {THEMES[self.current_theme]['scroll_bar']} }}"
            )

        # Reload to apply theme
        self.load_history()


if __name__ == "__main__":
    from storage import StorageManager

    app = QApplication(sys.argv)
    storage = StorageManager("history.db")
    window = MainWindow(storage)
    window.show()
    sys.exit(app.exec_())
