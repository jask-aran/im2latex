import sqlite3
import os
from pathlib import Path
from datetime import datetime
import shutil


class StorageManager:
    def __init__(self, db_path="history.db", screenshots_dir="screenshots"):
        self.db_path = Path(db_path)
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)  # Create folder if it doesn’t exist
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
        # Delete the screenshots folder and its contents
        if self.screenshots_dir.exists():
            shutil.rmtree(self.screenshots_dir)
        self.screenshots_dir.mkdir()  # Recreate the empty folder

        # Drop and recreate the table
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS screenshots")
            conn.commit()
        self.initialize_db()
        print("Database and screenshots reset successfully.")

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
                (str(image_path), entry_id),
            )
            conn.commit()

        print(f"Saved entry: ID={entry_id}, Timestamp={timestamp}, Shortcut={shortcut}")

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
            return cursor.fetchall()

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
