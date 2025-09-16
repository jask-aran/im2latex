"""PyQt chat window wired to the ChatApiManager."""
from __future__ import annotations

from typing import List, Dict

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QFrame,
)

from api_manager import ChatApiManager


class ChatApp(QWidget):
    """Simple chat UI that delegates API calls to ``ChatApiManager``."""

    def __init__(self, chat_manager: ChatApiManager, parent: QWidget | None = None):
        super().__init__(parent)
        if chat_manager is None:
            raise ValueError("chat_manager is required")

        self.chat_manager = chat_manager
        self.conversation: List[Dict[str, str]] = []
        self.awaiting_response = False

        self.chat_manager.chat_response_ready.connect(self._handle_response)
        self.chat_manager.chat_error.connect(self._handle_error)

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle("Chat Window")
        self.setGeometry(100, 100, 400, 500)

        layout = QVBoxLayout()

        self.response_area = QTextEdit()
        self.response_area.setReadOnly(True)
        self.response_area.setFont(QFont("Arial", 10))
        self.response_area.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.response_area.setMinimumHeight(300)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setFont(QFont("Arial", 10))
        self.input_field.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        layout.addWidget(self.response_area)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def send_message(self) -> None:
        if self.awaiting_response:
            return

        message = self.input_field.text().strip()
        if not message:
            return

        self._append_message("You", message)
        self.input_field.clear()

        pending_message = {"role": "user", "content": message}
        self.conversation.append(pending_message)

        if not self.chat_manager.send_chat_request(list(self.conversation)):
            self.conversation.pop()
            self._append_message(
                "System", "Unable to send message right now. Please try again."
            )
            return

        self.awaiting_response = True
        self._set_loading_state(True)

    def add_response(self, response: str) -> None:
        self.conversation.append({"role": "assistant", "content": response})
        self._append_message("Assistant", response)

    def clear_chat(self) -> None:
        self.conversation.clear()
        self.response_area.clear()

    def _append_message(self, speaker: str, message: str) -> None:
        self.response_area.append(f"{speaker}: {message}")
        self.response_area.append("")

    def _set_loading_state(self, is_loading: bool) -> None:
        self.input_field.setDisabled(is_loading)
        self.send_button.setDisabled(is_loading)
        self.send_button.setText("Sending..." if is_loading else "Send")

    @pyqtSlot(str)
    def _handle_response(self, response_text: str) -> None:
        self.awaiting_response = False
        self._set_loading_state(False)
        self.add_response(response_text)

    @pyqtSlot(str)
    def _handle_error(self, error_message: str) -> None:
        self.awaiting_response = False
        self._set_loading_state(False)
        self._append_message("System", f"Error: {error_message}")
