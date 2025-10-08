import json
import importlib

import pytest

import main as main_module


@pytest.fixture
def main():
    """Reload the :mod:`main` module for a clean ``ConfigManager`` each test."""

    # Ensure ``sys.exit`` is restored after potential monkeypatching in other tests.
    module = importlib.reload(main_module)
    return module


@pytest.fixture
def message_box_stub(monkeypatch, main):
    """Provide a stub :class:`QMessageBox` that records invocations."""

    class DummyMessageBox:
        Critical = object()
        ActionRole = object()
        Ok = object()
        instances = []

        def __init__(self):
            DummyMessageBox.instances.append(self)
            self.icons = []
            self.titles = []
            self.texts = []
            self.buttons = []
            self.clicked = None

        def setIcon(self, icon):
            self.icons.append(icon)

        def setWindowTitle(self, title):
            self.titles.append(title)

        def setText(self, text):
            self.texts.append(text)

        def addButton(self, *args):
            if len(args) == 2:
                label, role = args
            elif len(args) == 1:
                label, role = args[0], None
            else:  # pragma: no cover - defensive path for unexpected usage
                raise TypeError("Unexpected arguments for addButton")
            button = object()
            self.buttons.append((label, role, button))
            return button

        def exec_(self):
            return 0

        def clickedButton(self):
            return self.clicked

    DummyMessageBox.instances.clear()
    monkeypatch.setattr(main, "QMessageBox", DummyMessageBox)
    return DummyMessageBox


def test_config_manager_loads_existing_file(tmp_path, main):
    config_path = tmp_path / "config.json"
    config_data = {
        "api_key": "abc123",
        "prompts": {"math2latex": "prompt text", "table": "table prompt"},
        "shortcuts": {"windows": []},
    }
    config_path.write_text(json.dumps(config_data))

    manager = main.ConfigManager(str(config_path), main.DEFAULT_CONFIG)

    assert manager.get_config() == config_data
    assert manager.get_api_key() == "abc123"
    assert manager.get_prompt("math2latex") == "prompt text"
    assert manager.get_prompt("unknown") == ""


def test_config_manager_creates_default_on_error(
    tmp_path, monkeypatch, main, message_box_stub
):
    config_path = tmp_path / "config.json"
    config_path.write_text("not-json")

    monkeypatch.setattr(main.os, "startfile", lambda *_: None, raising=False)

    def exit_stub(code):
        raise SystemExit(code)

    monkeypatch.setattr(main.sys, "exit", exit_stub)

    with pytest.raises(SystemExit) as exc:
        main.ConfigManager(str(config_path), main.DEFAULT_CONFIG)

    assert exc.value.code == 1
    assert message_box_stub.instances, "An error dialog should be shown"

    written_data = json.loads(config_path.read_text())
    assert written_data == main.DEFAULT_CONFIG
