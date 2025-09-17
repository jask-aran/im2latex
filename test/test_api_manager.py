from types import SimpleNamespace

import pytest
from PIL import Image

import api_manager


class RecordingModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self.response_text)


def create_image():
    return Image.new("RGB", (4, 4), "white")


def test_api_worker_emits_finished_with_clean_text():
    models = RecordingModels("```latex\nx\\ny\n```")
    client = SimpleNamespace(models=models)
    image = create_image()
    worker = api_manager.ApiWorker(client, "prompt", "action", image)

    results = []
    worker.finished.connect(lambda text, action, img: results.append((text, action, img)))

    worker.process()

    assert results == [("x\\ny", "action", image)]
    assert models.calls == [
        {"model": "gemini-2.0-flash", "contents": ["prompt", image]}
    ]


def test_api_worker_emits_error_on_failure():
    class FailingModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("boom")

    client = SimpleNamespace(models=FailingModels())
    image = create_image()
    worker = api_manager.ApiWorker(client, "prompt", "action", image)

    errors = []
    worker.error.connect(errors.append)

    worker.process()

    assert errors == ["boom"]


def test_chat_worker_formats_conversation():
    models = RecordingModels("Answer")
    client = SimpleNamespace(models=models)
    conversation = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "system", "content": "Use markdown."},
        {"role": "user", "content": "   "},
    ]

    worker = api_manager.ChatApiWorker(client, conversation)
    responses = []
    worker.finished.connect(responses.append)

    worker.process()

    assert responses == ["Answer"]
    assert models.calls == [
        {
            "model": "gemini-2.0-flash",
            "contents": [
                "User: Hello",
                "Assistant: Hi!",
                "System: Use markdown.",
            ],
        }
    ]


def test_chat_worker_emits_error_for_empty_input():
    models = RecordingModels("unused")
    client = SimpleNamespace(models=models)

    worker = api_manager.ChatApiWorker(client, [])
    errors = []
    worker.error.connect(errors.append)

    worker.process()

    assert errors
    assert "No content" in errors[0]


def test_api_manager_updates_api_key(monkeypatch):
    created_keys = []

    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = SimpleNamespace(generate_content=lambda **kwargs: None)
            created_keys.append(api_key)

    monkeypatch.setattr(api_manager.genai, "Client", DummyClient)

    manager = api_manager.ApiManager("initial")
    assert created_keys == ["initial"]

    manager.update_api_key("updated")
    assert created_keys == ["initial", "updated"]
    assert manager.client.api_key == "updated"
