"""PyQt chat window wired to the ChatApiManager."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Dict, List, Tuple

from PIL import Image
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from api_manager import ChatApiManager
from storage import StorageManager

HistoryProvider = Callable[[], Sequence[Tuple[Any, ...]]]


class _ImageLoadWorker(QObject):
    """Load images off the UI thread to keep the chat responsive."""

    finished = pyqtSignal(Image.Image)
    error = pyqtSignal(str)

    def __init__(self, image_path: str) -> None:
        super().__init__()
        self._image_path = image_path

    @pyqtSlot()
    def load(self) -> None:
        try:
            with Image.open(self._image_path) as image:
                pil_image = image.copy()
        except FileNotFoundError:
            self.error.emit("Unable to locate the most recent screenshot on disk.")
            return
        except Exception as exc:  # pragma: no cover - defensive path
            self.error.emit(f"Failed to load screenshot: {exc}")
            return

        try:
            pil_image.load()
        except Exception as exc:  # pragma: no cover - defensive path
            self.error.emit(f"Failed to prepare screenshot: {exc}")
            return

        self.finished.emit(pil_image)


class ChatApp(QWidget):
    """Simple chat UI that delegates API calls to ``ChatApiManager``."""

    def __init__(
        self,
        chat_manager: ChatApiManager,
        history_source: StorageManager | HistoryProvider | None = None,
        parent: QWidget | None = None,
    ) -> None:
        if isinstance(history_source, QWidget) and parent is None:
            parent = history_source
            history_source = None

        super().__init__(parent)
        if chat_manager is None:
            raise ValueError("chat_manager is required")

        self.chat_manager = chat_manager
        self._history_source: StorageManager | HistoryProvider | None = history_source
        self.conversation: List[Dict[str, Any]] = []
        self.awaiting_response = False
        self._image_loader_thread: QThread | None = None
        self._image_loader: _ImageLoadWorker | None = None
        self._image_loading = False

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

        self.insert_text_button = QPushButton("Insert Last Text")
        self.insert_text_button.clicked.connect(self.insert_last_text)

        self.insert_image_button = QPushButton("Insert Last Image")
        self.insert_image_button.clicked.connect(self.insert_last_image)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.insert_text_button)
        button_layout.addWidget(self.insert_image_button)

        layout.addWidget(self.response_area)
        layout.addWidget(self.input_field)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self._update_insert_buttons_state()

    def send_message(self) -> None:
        if self.awaiting_response:
            return

        message = self.input_field.text().strip()
        has_pending_image = (
            bool(self.conversation)
            and isinstance(self.conversation[-1], dict)
            and self.conversation[-1].get("role") == "user"
            and self.conversation[-1].get("image") is not None
        )

        if not message and not has_pending_image:
            return

        pending_message: Dict[str, Any] | None = None
        if message:
            self._append_message("You", message)
            self.input_field.clear()

            pending_message = {"role": "user", "content": message}
            self.conversation.append(pending_message)

        if not self.chat_manager.send_chat_request(list(self.conversation)):
            if pending_message is not None and self.conversation:
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

    def insert_last_text(self) -> None:
        if self.awaiting_response:
            return

        try:
            entries = self._fetch_history_entries()
        except Exception as exc:  # pragma: no cover - defensive path
            self._append_message("System", f"Unable to access history: {exc}")
            return

        if not entries:
            self._append_message("System", "No saved responses available.")
            return

        latest = entries[0]
        raw_response = latest[4] if len(latest) > 4 else None
        if not isinstance(raw_response, str) or not raw_response.strip():
            self._append_message(
                "System", "The most recent entry does not include a response text."
            )
            return

        self.input_field.setText(raw_response)
        self.input_field.setFocus()
        self.input_field.setCursorPosition(len(raw_response))

    def insert_last_image(self) -> None:
        if self.awaiting_response:
            return

        try:
            entries = self._fetch_history_entries()
        except Exception as exc:  # pragma: no cover - defensive path
            self._append_message("System", f"Unable to access history: {exc}")
            return

        if not entries:
            self._append_message("System", "No saved screenshots available.")
            return

        latest = entries[0]
        image_path = latest[2] if len(latest) > 2 else None
        if not isinstance(image_path, str) or not image_path:
            self._append_message(
                "System", "The most recent entry does not include a screenshot path."
            )
            return

        if self._image_loading:
            return

        self._image_loader_thread = QThread()
        self._image_loader = _ImageLoadWorker(image_path)
        self._image_loader.moveToThread(self._image_loader_thread)
        self._image_loader_thread.started.connect(self._image_loader.load)
        self._image_loader.finished.connect(self._on_image_loaded)
        self._image_loader.error.connect(self._on_image_error)
        self._image_loader.finished.connect(self._cleanup_image_loader)
        self._image_loader.error.connect(self._cleanup_image_loader)
        self._image_loading = True
        self._update_insert_buttons_state()
        try:
            self._image_loader_thread.start()
        except Exception as exc:  # pragma: no cover - defensive path
            self._append_message("System", f"Unable to load screenshot: {exc}")
            self._cleanup_image_loader()

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
        self._update_insert_buttons_state(is_loading)

    def _update_insert_buttons_state(self, is_loading: bool | None = None) -> None:
        if not hasattr(self, "insert_text_button"):
            return

        base_disabled = is_loading if is_loading is not None else self.awaiting_response
        disabled = base_disabled or self._image_loading
        has_history = self._history_source is not None
        self.insert_text_button.setDisabled(disabled or not has_history)
        self.insert_image_button.setDisabled(disabled or not has_history)

    def _fetch_history_entries(self) -> List[Tuple[Any, ...]]:
        if self._history_source is None:
            return []

        if isinstance(self._history_source, StorageManager):
            result = self._history_source.get_all_entries() or []
        elif callable(self._history_source):
            result = self._history_source() or []
        else:  # pragma: no cover - defensive path
            return []

        return list(result)

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

    @pyqtSlot(Image.Image)
    def _on_image_loaded(self, pil_image: Image.Image) -> None:
        image_message: Dict[str, Any] = {
            "role": "user",
            "image": pil_image,
            "content": "",
        }
        self.conversation.append(image_message)
        self._append_message("You", "[Image attached]")

    @pyqtSlot(str)
    def _on_image_error(self, message: str) -> None:
        self._append_message("System", message)

    def _cleanup_image_loader(self) -> None:
        if self._image_loader_thread:
            self._image_loader_thread.quit()
            self._image_loader_thread.wait()
            self._image_loader_thread.deleteLater()
            self._image_loader_thread = None
        if self._image_loader:
            self._image_loader.deleteLater()
            self._image_loader = None
        self._image_loading = False
        self._update_insert_buttons_state()
