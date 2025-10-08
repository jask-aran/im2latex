from pathlib import Path

import pytest
from PIL import Image

from storage import StorageManager


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "history.db"
    screenshots_dir = tmp_path / "shots"
    return StorageManager(db_path=db_path, screenshots_dir=screenshots_dir)


def create_sample_image(color="white"):
    return Image.new("RGB", (10, 10), color=color)


def test_save_entry_persists_image_and_metadata(storage):
    image = create_sample_image()
    storage.save_entry(image, "prompt", "response", "shortcut")

    entries = storage.get_all_entries()
    assert len(entries) == 1
    entry = entries[0]

    image_path = Path(entry[2])
    assert image_path.exists(), "Screenshot should be saved to disk"

    with Image.open(image_path) as saved_image:
        assert saved_image.size == (10, 10)

    assert entry[3] == "prompt"
    assert entry[4] == "response"
    assert entry[5] == "shortcut"
    assert entry[6] == "latex"


def test_reset_db_removes_entries_and_files(storage):
    image = create_sample_image(color="blue")
    storage.save_entry(image, "prompt", "response", "shortcut")

    assert any(storage.screenshots_dir.iterdir())

    storage.reset_db()

    assert storage.get_all_entries() == []
    assert storage.screenshots_dir.exists()
    assert list(storage.screenshots_dir.iterdir()) == []
