# gui.py
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QLabel,
    QTextEdit,
    QScrollArea,
    QFrame,
    QListWidgetItem,
    QApplication,
    QPushButton,
    QFileDialog,
)
from PyQt5.QtGui import QIcon, QPixmap, QImage, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from storage import StorageManager
from PIL import Image


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class HistoryItem(QWidget):
    """Custom widget for each history item"""

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        (
            self.id,
            self.timestamp,
            self.image_path,
            _,
            self.raw_response,
            self.action,
            _,
        ) = entry
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Add timestamp and action as header
        header_layout = QHBoxLayout()

        # Format timestamp
        try:
            dt = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
            formatted_time = dt.strftime("%b %d, %Y - %H:%M:%S")
        except ValueError:
            formatted_time = self.timestamp

        timestamp_label = QLabel(formatted_time)
        timestamp_label.setStyleSheet("font-weight: bold; color: #333;")

        action_label = QLabel(self.action)
        action_label.setStyleSheet("color: #666; font-style: italic;")

        header_layout.addWidget(timestamp_label)
        header_layout.addStretch()
        header_layout.addWidget(action_label)

        layout.addLayout(header_layout)

        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        layout.addWidget(line)

        # Image and response in a horizontal layout
        content_layout = QHBoxLayout()

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 100)
        self.image_label.setMaximumSize(400, 300)
        self.image_label.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ddd;"
        )

        # Load and scale image
        try:
            img = Image.open(self.image_path)
            # Calculate scaling while preserving aspect ratio
            img_width, img_height = img.size
            max_width, max_height = 400, 300

            # Calculate scaling factor
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale_factor = min(width_ratio, height_ratio)

            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            qimage = QImage(
                img.tobytes(),
                img.width,
                img.height,
                img.width * 3 if img.mode == "RGB" else img.width * 4,
                QImage.Format_RGB888 if img.mode == "RGB" else QImage.Format_RGBA8888,
            )
            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)

        except Exception as e:
            self.image_label.setText(f"Error loading image: {e}")

        # Response text
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setText(self.raw_response)
        self.response_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """
        )
        self.response_text.setMinimumHeight(100)

        # Add image and response to the content layout
        content_layout.addWidget(self.image_label, 2)  # 2 parts for image
        content_layout.addWidget(self.response_text, 3)  # 3 parts for text

        layout.addLayout(content_layout)

        # Add action buttons
        button_layout = QHBoxLayout()

        # Copy button
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.setStyleSheet(
            """
            QPushButton {
                background-color: #5c85d6;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a70d6;
            }
        """
        )
        copy_button.clicked.connect(self.copy_to_clipboard)

        # Save image button
        save_image_button = QPushButton("Save Image")
        save_image_button.setStyleSheet(
            """
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """
        )
        save_image_button.clicked.connect(self.save_image)

        button_layout.addWidget(copy_button)
        button_layout.addWidget(save_image_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Add some spacing at the bottom
        layout.addSpacing(10)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.raw_response)

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


class MainWindow(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self, storage_manager):
        super().__init__()
        self.storage_manager = storage_manager
        self.entries = []
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        self.setWindowTitle("Im2Latex History")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(resource_path("assets/scissor.png")))

        # Set application style
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QScrollArea {
                border: none;
                background-color: white;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #e7f0fd;
                color: #333;
            }
        """
        )

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header with title
        header = QLabel("Im2Latex History")
        header.setStyleSheet(
            """
            font-size: 22px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        """
        )
        main_layout.addWidget(header)

        # Container for history items
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(15)  # Space between items

        # Scroll area for history items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.history_container)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_layout.addWidget(scroll_area)

        # Load initial history
        self.load_history()

        # Connect refresh signal
        self.refresh_signal.connect(self.load_history)

    def setup_timer(self):
        """Set up a timer to refresh the history periodically."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(2000)  # Check every 2 seconds

    def check_for_updates(self):
        """Check if there are new entries in the database."""
        current_entries = self.storage_manager.get_all_entries()
        if len(current_entries) != len(self.entries):
            self.refresh_signal.emit()

    def load_history(self):
        """Load or refresh history from the database."""
        # Clear existing widgets from layout
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get entries from database
        self.entries = self.storage_manager.get_all_entries()

        if not self.entries:
            # Show a message if no history entries
            no_history_label = QLabel(
                "No history entries found. Take some screenshots!"
            )
            no_history_label.setAlignment(Qt.AlignCenter)
            no_history_label.setStyleSheet(
                """
                font-size: 16px;
                color: #888;
                padding: 50px;
            """
            )
            self.history_layout.addWidget(no_history_label)
            return

        # Add history items
        for entry in self.entries:
            history_item = HistoryItem(entry)

            # Add item frame
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.StyledPanel)
            item_frame.setStyleSheet(
                """
                QFrame {
                    background-color: white;
                    border-radius: 6px;
                    border: 1px solid #ddd;
                }
            """
            )

            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.addWidget(history_item)

            self.history_layout.addWidget(item_frame)

        # Add stretch at the end to push items to the top
        self.history_layout.addStretch()
