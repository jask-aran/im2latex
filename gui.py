import os
import sys
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


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class OverlayWidget(QWidget):
    """Widget that displays an image overlay on top of the parent window"""

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
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
        painter.fillRect(
            self.rect(), QColor(0, 0, 0, 178)
        )  # Semi-transparent black background

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


class HistoryItem(QWidget):
    """Widget representing a single history entry"""

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        (
            self.id,
            self.timestamp,
            self.image_path,
            _,  # Unused field
            self.raw_response,
            self.action,
            _,  # Unused field
        ) = entry
        self.pixmap = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header section
        self._setup_header(layout)

        # Content section
        self._setup_content(layout)

        # Buttons section
        self._setup_buttons(layout)

    def _setup_header(self, layout):
        """Setup the header section with timestamp and action"""
        header_layout = QHBoxLayout()

        # Format timestamp
        try:
            dt = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
            formatted_time = dt.strftime("%b %d, %Y - %H:%M:%S")
        except ValueError:
            formatted_time = self.timestamp

        timestamp_label = QLabel(formatted_time)
        timestamp_label.setStyleSheet("font-weight: bold; color: #333;")
        timestamp_label.setFixedHeight(20)

        action_label = QLabel(self.action)
        action_label.setStyleSheet("color: #666; font-style: italic;")
        action_label.setFixedHeight(20)

        header_layout.addWidget(timestamp_label)
        header_layout.addStretch()
        header_layout.addWidget(action_label)
        layout.addLayout(header_layout)

        # Add separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        layout.addWidget(line)

    def _setup_content(self, layout):
        """Setup the content section with image and response text"""
        content_layout = QHBoxLayout()

        # Image section
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 150)
        self.image_label.setMaximumSize(400, 400)
        self.image_label.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ddd;"
        )
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.show_image_overlay

        # Load and display the image
        self._load_image()

        # Response text section
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setText(self.raw_response)
        self.response_text.setStyleSheet(
            "QTextEdit { background-color: #f8f8f8; border: 1px solid #ddd; "
            "border-radius: 4px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; }"
        )
        self.response_text.setMinimumHeight(150)

        content_layout.addWidget(self.image_label, 2)
        content_layout.addWidget(self.response_text, 3)
        layout.addLayout(content_layout)

    def _load_image(self):
        """Load and prepare the image for display"""
        try:
            img = Image.open(self.image_path)
            img_width, img_height = img.size

            # Calculate scaling to fit within constraints
            max_width, max_height = 400, 400
            scale_factor = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)

            # Resize the image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert PIL image to QImage
            if img.mode == "RGB":
                qimage = QImage(
                    img.tobytes(),
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format_RGB888,
                )
            else:  # RGBA
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

    def _setup_buttons(self, layout):
        """Setup the button section"""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)
        button_layout.setSpacing(10)

        # Copy button
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.setStyleSheet(
            "QPushButton { background-color: #5c85d6; color: white; border: none; "
            "padding: 5px 10px; border-radius: 3px; max-height: 30px; } "
            "QPushButton:hover { background-color: #3a70d6; }"
        )
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setFixedHeight(30)

        # Save image button
        save_image_button = QPushButton("Save Image")
        save_image_button.setStyleSheet(
            "QPushButton { background-color: #5cb85c; color: white; border: none; "
            "padding: 5px 10px; border-radius: 3px; max-height: 30px; } "
            "QPushButton:hover { background-color: #4cae4c; }"
        )
        save_image_button.clicked.connect(self.save_image)
        save_image_button.setFixedHeight(30)

        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(save_image_button)

        # Add the LaTeX button if this is a math2latex action, but keep it disabled
        if self.action == "math2latex":
            latex_button = QPushButton("Render LaTeX")
            latex_button.setStyleSheet(
                "QPushButton { background-color: #999999; color: white; border: none; "
                "padding: 5px 10px; border-radius: 3px; max-height: 30px; }"
            )
            latex_button.setEnabled(False)  # Disabled as requested
            latex_button.setFixedHeight(30)
            button_layout.addWidget(latex_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def show_image_overlay(self, event):
        """Show the image in a full-screen overlay"""
        if self.pixmap:
            overlay = OverlayWidget(self.pixmap, self.window())
            overlay.show()

    def copy_to_clipboard(self):
        """Copy the response text to clipboard with visual feedback"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.raw_response)

        # Visual feedback for copy action
        original_text = self.copy_button.text()
        original_style = self.copy_button.styleSheet()

        self.copy_button.setText("Copied! ✓")
        self.copy_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border: none; "
            "padding: 5px 10px; border-radius: 3px; max-height: 30px; }"
        )

        # Reset button after delay
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
        QTimer.singleShot(1500, lambda: self.copy_button.setStyleSheet(original_style))

    def save_image(self):
        """Save the image to a user-selected location"""
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


class MainWindow(QMainWindow):
    """Main application window"""

    refresh_signal = pyqtSignal()

    def __init__(self, storage_manager):
        super().__init__()
        self.storage_manager = storage_manager
        self.entries = []
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        self.setWindowTitle("Im2Latex")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(resource_path("assets/scissor.png")))
        self.setStyleSheet("QMainWindow { background-color: #f5f5f5; }")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QLabel("Im2Latex History")
        header.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #333; margin-bottom: 10px;"
        )
        main_layout.addWidget(header)

        # History container with scrolling
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(15)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.history_container)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background-color: white; }"
        )
        main_layout.addWidget(scroll_area)

        # Load initial history
        self.load_history()
        self.refresh_signal.connect(self.load_history)

    def setup_timer(self):
        """Setup timer to periodically check for new entries"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(2000)  # Check every 2 seconds

    def check_for_updates(self):
        """Check if there are new entries to display"""
        current_entries = self.storage_manager.get_all_entries()
        if len(current_entries) != len(self.entries):
            self.refresh_signal.emit()

    def load_history(self):
        """Load and display history entries"""
        # Clear existing widgets
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Get fresh entries
        self.entries = self.storage_manager.get_all_entries()

        # Show message if no entries
        if not self.entries:
            no_history_label = QLabel(
                "No history entries found. Take some screenshots!"
            )
            no_history_label.setAlignment(Qt.AlignCenter)
            no_history_label.setStyleSheet(
                "font-size: 16px; color: #888; padding: 50px;"
            )
            self.history_layout.addWidget(no_history_label)
            return

        # Add history items
        for entry in self.entries:
            history_item = HistoryItem(entry)
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.StyledPanel)
            item_frame.setStyleSheet(
                "QFrame { background-color: white; border-radius: 6px; border: 1px solid #ddd; }"
            )
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.addWidget(history_item)
            self.history_layout.addWidget(item_frame)

        # Add stretch at the end to push items to the top
        self.history_layout.addStretch()


if __name__ == "__main__":
    from storage import StorageManager  # Assuming this is defined elsewhere

    app = QApplication(sys.argv)
    storage = StorageManager("history.db")  # Example database
    window = MainWindow(storage)
    window.show()
    sys.exit(app.exec_())
