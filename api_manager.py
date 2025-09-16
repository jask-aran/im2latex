"""API manager classes handling background Gemini requests for screenshots and chat."""
from __future__ import annotations

from typing import List, Dict, Any

from PIL import Image
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from google import genai


class ApiWorker(QObject):
    """Worker object responsible for screenshot-to-LaTeX requests."""

    finished = pyqtSignal(str, str, Image.Image)  # response_text, action, image
    error = pyqtSignal(str)

    def __init__(self, client: genai.Client, prompt_text: str, action: str, image: Image.Image):
        super().__init__()
        self.client = client
        self.prompt_text = prompt_text
        self.action = action
        self.image = image

    @pyqtSlot()
    def process(self) -> None:
        """Execute the Gemini request in a background thread."""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=[self.prompt_text, self.image]
            )
            response_text = response.text

            if not response_text:
                raise ValueError("API returned an empty or invalid response")

            response_text = response_text.strip()
            if response_text.startswith("```latex") or response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[-1].rsplit("\n", 1)[0]
            response_text = response_text.strip()

            self.finished.emit(response_text, self.action, self.image)
        except Exception as exc:  # pragma: no cover - defensive path
            self.error.emit(str(exc))


class ChatApiWorker(QObject):
    """Worker object responsible for conversational Gemini requests."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client: genai.Client, conversation: List[Dict[str, Any]]):
        super().__init__()
        self.client = client
        self.conversation = conversation

    @pyqtSlot()
    def process(self) -> None:
        try:
            contents: List[str] = []
            for message in self.conversation:
                role = message.get("role", "user")
                content = message.get("content", "").strip()
                if not content:
                    continue
                if role == "assistant":
                    prefix = "Assistant"
                elif role == "system":
                    prefix = "System"
                else:
                    prefix = "User"
                contents.append(f"{prefix}: {content}")

            if not contents:
                raise ValueError("No content to send to chat API")

            response = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=contents
            )

            response_text = (response.text or "").strip()
            if not response_text:
                raise ValueError("API returned an empty or invalid response")

            self.finished.emit(response_text)
        except Exception as exc:  # pragma: no cover - defensive path
            self.error.emit(str(exc))


class ApiManager(QObject):
    """Manages screenshot pipeline Gemini requests via QThreads."""

    api_response_ready = pyqtSignal(str, str, Image.Image)
    api_error = pyqtSignal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self.client = genai.Client(api_key=api_key)
        self.thread: QThread | None = None
        self.worker: ApiWorker | None = None
        self.api_in_progress = False

    def update_api_key(self, api_key: str) -> None:
        """Refresh the Gemini client when the API key changes."""
        self.client = genai.Client(api_key=api_key)

    def send_request(self, image: Image.Image, prompt_text: str, action: str) -> bool:
        self.api_in_progress = True

        self.thread = QThread()
        self.worker = ApiWorker(self.client, prompt_text, action, image)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self._handle_response)
        self.worker.error.connect(self._handle_error)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)
        self.thread.start()
        return True

    @pyqtSlot(str, str, Image.Image)
    def _handle_response(self, response_text: str, action: str, image: Image.Image) -> None:
        self.api_response_ready.emit(response_text, action, image)
        self.api_in_progress = False

    @pyqtSlot(str)
    def _handle_error(self, error_message: str) -> None:
        self.api_error.emit(error_message)
        self.api_in_progress = False

    def _cleanup_thread(self) -> None:
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        if self.thread:
            self.thread.deleteLater()
            self.thread = None

    def cleanup(self) -> None:
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        if self.thread:
            self.thread.deleteLater()
            self.thread = None

        self.api_in_progress = False


class ChatApiManager(QObject):
    """Manages chat Gemini requests via QThreads."""

    chat_response_ready = pyqtSignal(str)
    chat_error = pyqtSignal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self.client = genai.Client(api_key=api_key)
        self.thread: QThread | None = None
        self.worker: ChatApiWorker | None = None
        self.chat_in_progress = False

    def update_api_key(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)

    def send_chat_request(self, conversation: List[Dict[str, Any]]) -> bool:
        if self.chat_in_progress or not conversation:
            return False

        conversation_copy = [dict(message) for message in conversation]

        self.thread = QThread()
        self.worker = ChatApiWorker(self.client, conversation_copy)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self._handle_response)
        self.worker.error.connect(self._handle_error)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.error.connect(self._cleanup_thread)

        self.chat_in_progress = True
        self.thread.start()
        return True

    @pyqtSlot(str)
    def _handle_response(self, response_text: str) -> None:
        self.chat_in_progress = False
        self.chat_response_ready.emit(response_text)

    @pyqtSlot(str)
    def _handle_error(self, error_message: str) -> None:
        self.chat_in_progress = False
        self.chat_error.emit(error_message)

    def _cleanup_thread(self) -> None:
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        if self.thread:
            self.thread.deleteLater()
            self.thread = None

    def cleanup(self) -> None:
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        if self.thread:
            self.thread.deleteLater()
            self.thread = None

        self.chat_in_progress = False
