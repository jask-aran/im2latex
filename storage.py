import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

from PyQt5.QtCore import QObject, pyqtSignal


class StorageManager(QObject):
    entry_saved = pyqtSignal()
    history_reset = pyqtSignal()

    def __init__(self, db_path="history.db", screenshots_dir="screenshots"):
        super().__init__()
        self.db_path = Path(db_path)
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.initialize_db()

    def initialize_db(self):
        """Initialize the SQLite database and create the table if it doesn’t exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    raw_response TEXT,
                    shortcut TEXT NOT NULL,
                    output_type TEXT DEFAULT 'latex'
                )
            """
            )
            conn.commit()

    def reset_db(self):
        """Reset the database and delete all saved screenshots."""
        if self.screenshots_dir.exists():
            shutil.rmtree(self.screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        if self.db_path.exists():
            self.db_path.unlink()

        self.initialize_db()
        print("Database and screenshots reset successfully.")
        self.history_reset.emit()

    def save_entry(self, image, prompt, raw_response, shortcut):
        """Save the screenshot and metadata to the filesystem and database."""
        # Generate timestamp and ID will be assigned by SQLite
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Insert into database first to get the ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO screenshots (timestamp, image_path, prompt, raw_response, shortcut, output_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (timestamp, "", prompt, raw_response, shortcut, "latex"),
            )
            entry_id = cursor.lastrowid
            conn.commit()

        # Save image with ID and timestamp in filename
        image_filename = f"{entry_id}_{timestamp}.png"
        image_path = self.screenshots_dir / image_filename
        image.save(image_path, "PNG")

        # Update the image_path in the database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE screenshots SET image_path = ? WHERE id = ?
            """,
                (image_filename, entry_id),
            )
            conn.commit()

        print(f"Saved entry: ID={entry_id}, Timestamp={timestamp}, Shortcut={shortcut}")
        self.entry_saved.emit()

    def get_all_entries(self):
        """Retrieve all entries in reverse chronological order."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, image_path, prompt, raw_response, shortcut, output_type
                FROM screenshots
                ORDER BY timestamp DESC
            """
            )
            rows = cursor.fetchall()

        resolved_rows = []
        for row in rows:
            row_list = list(row)
            stored_path = Path(row_list[2])
            resolved_path = (
                stored_path
                if stored_path.is_absolute()
                else (self.screenshots_dir / stored_path)
            )
            row_list[2] = str(resolved_path)
            resolved_rows.append(tuple(row_list))

        return resolved_rows

    def print_entries(self):
        """Print a basic representation of the database, focusing on raw responses."""
        entries = self.get_all_entries()
        if not entries:
            print("No entries in the database.")
            return

        print("\nDatabase Contents (Newest First):")
        print("-" * 50)
        for entry in entries:
            id, timestamp, image_path, prompt, raw_response, shortcut, output_type = (
                entry
            )
            print(f"ID: {id}")
            print(f"Timestamp: {timestamp}")
            print(f"Image Path: {image_path}")
            # print(f"Prompt: {prompt}")
            print(f"Raw Response: \n{raw_response}")
            print(f"Shortcut: {shortcut}")
            print(f"Output Type: {output_type}")
            print("-" * 50)
