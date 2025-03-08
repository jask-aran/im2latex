# gui.py
from PyQt5.QtWidgets import (
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt, QSize
from storage import StorageManager
import os
import sys
from PIL import Image


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class HistoryWindow(QMainWindow):
    def __init__(self, storage_manager):
        super().__init__()
        self.storage_manager = storage_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Im2Latex History")
        self.setGeometry(100, 100, 1000, 600)  # Increased width for image column
        self.setWindowIcon(QIcon(resource_path("assets/scissor.png")))

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Table widget to display history
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Updated: ID, Timestamp, Image, Response, Action
        self.table.setHorizontalHeaderLabels(
            ["ID", "Timestamp", "Image", "Response", "Action"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.table.setWordWrap(True)  # Enable text wrapping
        layout.addWidget(self.table)

        # Load data
        self.load_history()

    def load_history(self):
        entries = self.storage_manager.get_all_entries()
        self.table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            id, timestamp, image_path, _, raw_response, action, _ = (
                entry  # Ignore prompt
            )

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(id)))

            # Timestamp
            self.table.setItem(row, 1, QTableWidgetItem(timestamp))

            # Image (scaled down)
            try:
                img = Image.open(image_path)
                # Scale image to max 100x100 while preserving aspect ratio
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                qpixmap = QPixmap.fromImage(
                    QImage(
                        img.tobytes(),
                        img.width,
                        img.height,
                        img.width * 3 if img.mode == "RGB" else img.width * 4,
                        (
                            QImage.Format_RGB888
                            if img.mode == "RGB"
                            else QImage.Format_RGBA8888
                        ),
                    )
                )
                image_label = QLabel()
                image_label.setPixmap(qpixmap)
                image_label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row, 2, image_label)
                self.table.setRowHeight(
                    row, max(100, self.table.rowHeight(row))
                )  # Adjust row height
            except Exception as e:
                self.table.setItem(row, 2, QTableWidgetItem(f"Error: {e}"))

            # Response (with wrapping)
            response_item = QTableWidgetItem(raw_response)
            response_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.table.setItem(row, 3, response_item)

            # Action (formerly Shortcut)
            self.table.setItem(row, 4, QTableWidgetItem(action))

        # Adjust column widths
        self.table.resizeColumnsToContents()
        # Set fixed width for Image column
        self.table.setColumnWidth(2, 120)  # Slightly wider than 100 for padding
        # Ensure Response column stretches appropriately
        self.table.horizontalHeader().setSectionResizeMode(
            3, self.table.horizontalHeader().Stretch
        )
