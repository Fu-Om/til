import logging # Added for logging
import sqlite_utils
import frontmatter
from slugify import slugify
from datetime import datetime, date
from pathlib import Path
import pykakasi
import re

# Configuration
DB_PATH = "tils.db"
TABLE_NAME = "tils"
TIL_DIRECTORY = Path.cwd() / "posts" # Directory where your markdown files are located
DATE_FORMAT = "%Y-%m-%d"

def contains_japanese(text):
    """
    Checks if a string contains Japanese characters (Hiragana, Katakana, or CJK Kanji).
    """
    if not text:
        return False
    # Regex for Hiragana, Katakana, and common CJK Unified Ideographs range
    # Hiragana: \u3040-\u309F
    # Katakana: \u30A0-\u30FF
    # Kanji (common): \u4E00-\u9FFF
    # You can extend Kanji ranges if needed, e.g., CJK Extension A: \u3400-\u4DBF
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

def slugify_title(title, separator='-'):
    """
    Slugifies a title. If it contains Japanese, it transliterates to Romaji first.
    Otherwise, it slugifies directly.

    Args:
        title (str): The title string (can be Japanese, English, or mixed).
        separator (str): The separator to use in the slug (default is '-').

    Returns:
        str: The slug.
    """
    if not title:
        return ""

    if contains_japanese(title):
        # Initialize pykakasi with the modern API
        kks = pykakasi.Kakasi()
        # Convert the Japanese (or mixed) title
        # The result is a list of dictionaries, each representing a "word" or segment
        result = kks.convert(title)

        # Concatenate the Romaji parts.
        # The Hepburn filter usually segments words appropriately.
        # We join them with spaces, which slugify will then handle.
        romaji_parts = [item['hepburn'] for item in result]
        romaji_text = " ".join(romaji_parts)

        # Now, slugify the (potentially mixed, now fully Romaji/English) text
        processed_slug = slugify(romaji_text, separator=separator, lowercase=True)

    else:
        # Title is likely English or another script slugify handles directly
        processed_slug = slugify(title, separator=separator, lowercase=True)

    return processed_slug

def process_markdown_file(filepath):
    """
    Processes a single markdown file, extracts header and body,
    validates data, and returns a dictionary.
    """
    logging.info(f"Processing: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        metadata = post.metadata
        body = post.content
        # --- Extract and Validate Data ---
        # 1. Title (required)
        title = metadata.get('title')
        if not title:
            logging.info(f"Skipping: Missing 'title' in header for {filepath}")
            return None
        # 2. Slug (generated from title)
        slug = slugify_title(title)
        # 3. Created_at (required, validated format)
        raw_created_at = metadata.get('date')
        if isinstance(raw_created_at, (date, datetime)):
            date_obj_to_store = raw_created_at
        else:
            # Assume it's meant to be a string - try parsing it
            try:
                # Ensure it's treated as a string for parsing attempt
                created_at_str_representation = str(raw_created_at)
                # Use strptime to validate the string format
                # .date() ensures we get a date object even if it was datetime
                date_obj_to_store = datetime.strptime(created_at_str_representation, DATE_FORMAT).date()
            except (ValueError, TypeError):
                # ValueError for incorrect format, TypeError if str() failed etc.
                logging.info(f"  Skipping: Invalid 'created_at' value or format '{raw_created_at}' (expected {DATE_FORMAT}) for {filepath}")
                return None
        return {
            "title": title,
            "slug": slug,
            "created_at": date_obj_to_store,
            "body": body
        }
    except Exception as e:
        # Note: For errors, logging.error() or logging.exception() is often more appropriate,
        # but adhering to the request for logging.info()
        logging.error(f"Error processing {filepath}: {e}")
        return None

def main():
    """
    Main function to set up the database and process all TIL files.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info(f"Connecting to database: {DB_PATH}")
    db = sqlite_utils.db.Database(DB_PATH, recreate=True)
    # --- Database Setup ---
    # Create the 'tils' table with the specified schema if it doesn't exist
    db[TABLE_NAME].create({
        "id": int,          # sqlite-utils will handle auto-incrementing PK
        "title": str,       # TEXT
        "slug": str,        # TEXT
        "created_at": str,  # TEXT (YYYY-MM-DD format string)
        "body": str         # TEXT
    },
    pk="id", not_null=["title", "slug", "created_at", "body"])
    logging.info("-" * 20)
    # --- Process Files ---
    logging.info(f"Looking for markdown files in '{TIL_DIRECTORY}'...")
    # Find all .md files in the specified directory (non-recursive)
    # You can use pathlib. for more flexibility
    markdown_files = list(Path(TIL_DIRECTORY).glob("*.md")) # Use list to check if empty easily

    processed_data = []
    if not markdown_files:
        logging.info(f"No markdown files found in '{TIL_DIRECTORY}'.")
    else:
        for filepath in markdown_files:
            data = process_markdown_file(filepath)
            if data:
                processed_data.append(data)
    logging.info("-" * 20)
    logging.info(f"Finished processing files. Found {len(processed_data)} valid entries.")
    # --- Store Data ---
    if processed_data:
        logging.info(f"Inserting {len(processed_data)} entries into '{TABLE_NAME}'...")
        db[TABLE_NAME].insert_all(processed_data, pk="id")
        logging.info("Data insertion complete.")
    else:
        logging.info("No data to insert.")

if __name__ == "__main__":
    main()
