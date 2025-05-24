import logging
import sqlite_utils
import frontmatter
from slugify import slugify
from datetime import datetime, date
from pathlib import Path
import pykakasi
import re

# Configuration
DB_PATH = "tils.db"
TILS_TABLE_NAME = "tils"
TAGS_TABLE_NAME = "tags"
TIL_TAGS_TABLE_NAME = "til_tags"
TIL_DIRECTORY = Path.cwd() / "posts" # Directory where your markdown files are located
DATE_FORMAT = "%Y-%m-%d"

def contains_japanese(text):
    """
    Checks if a string contains Japanese characters (Hiragana, Katakana, or CJK Kanji).
    """
    if not text:
        return False
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

def slugify_title(title, separator='-'):
    """
    Slugifies a title. If it contains Japanese, it transliterates to Romaji first.
    Otherwise, it slugifies directly.
    """
    if not title:
        return ""
    if contains_japanese(title):
        kks = pykakasi.Kakasi()
        result = kks.convert(title)
        romaji_parts = [item['hepburn'] for item in result]
        romaji_text = " ".join(romaji_parts)
        processed_slug = slugify(romaji_text, separator=separator, lowercase=True)
    else:
        processed_slug = slugify(title, separator=separator, lowercase=True)
    return processed_slug

def process_markdown_file(filepath):
    """
    Processes a single markdown file, extracts header and body,
    validates data, and returns a dictionary.
    """
    logging.info(f"Processing: {filepath.name}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        metadata = post.metadata
        body = post.content

        title = metadata.get('title')
        if not title:
            logging.warning(f"Skipping: Missing 'title' in header for {filepath.name}")
            return None

        slug = slugify_title(title)

        raw_created_at = metadata.get('date')
        if isinstance(raw_created_at, (date, datetime)):
            date_obj_to_store = raw_created_at.strftime(DATE_FORMAT) # Store as string
        elif isinstance(raw_created_at, str):
            try:
                # Validate and reformat if necessary, ensure it's stored as YYYY-MM-DD string
                date_obj_to_store = datetime.strptime(raw_created_at, DATE_FORMAT).strftime(DATE_FORMAT)
            except ValueError:
                logging.warning(f"Skipping: Invalid 'date' format '{raw_created_at}' (expected {DATE_FORMAT}) for {filepath.name}")
                return None
        else:
            logging.warning(f"Skipping: Invalid 'date' value type '{type(raw_created_at)}' for {filepath.name}")
            return None

        tags_list = metadata.get('tags', [])
        if not isinstance(tags_list, list):
            logging.warning(f"Warning: 'tags' in {filepath.name} is not a list, treating as no tags.")
            tags_list = []
        # Ensure tags are strings
        tags_list = [str(tag) for tag in tags_list if tag]


        return {
            "title": title,
            "slug": slug,
            "created_at": date_obj_to_store, # Store as string
            "body": body,
            "tags": tags_list # Add tags to the returned data
        }
    except Exception as e:
        logging.error(f"Error processing {filepath.name}: {e}", exc_info=True)
        return None

def main():
    """
    Main function to set up the database and process all TIL files.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info(f"Connecting to database: {DB_PATH}")
    db = sqlite_utils.db.Database(DB_PATH, recreate=True)

    # --- Database Setup ---
    logging.info(f"Creating table '{TILS_TABLE_NAME}'...")
    tils_table = db[TILS_TABLE_NAME]
    tils_table.create({
        "id": int,
        "title": str,
        "slug": str,
        "created_at": str, # Storing as TEXT in YYYY-MM-DD format
        "body": str
    }, pk="id", not_null=["title", "slug", "created_at", "body"])

    logging.info(f"Creating table '{TAGS_TABLE_NAME}'...")
    tags_table = db[TAGS_TABLE_NAME]
    tags_table.create({
        "tag_id": int,
        "name": str
    }, pk="tag_id", not_null=["name"])
    tags_table.create_index(["name"], unique=True) # Ensure tag names are unique

    logging.info(f"Creating table '{TIL_TAGS_TABLE_NAME}'...")
    til_tags_table = db[TIL_TAGS_TABLE_NAME]
    til_tags_table.create({
        "til_id": int,
        "tag_id": int
    }, pk=("til_id", "tag_id"), foreign_keys=[
        ("til_id", TILS_TABLE_NAME, "id"),
        ("tag_id", TAGS_TABLE_NAME, "tag_id")
    ])

    logging.info("-" * 20)
    logging.info(f"Looking for markdown files in '{TIL_DIRECTORY}'...")
    markdown_files = list(TIL_DIRECTORY.glob("*.md"))

    if not markdown_files:
        logging.info(f"No markdown files found in '{TIL_DIRECTORY}'.")
        return

    processed_count = 0
    for filepath in markdown_files:
        data = process_markdown_file(filepath)
        if data:
            # Extract tags before inserting into tils table
            tags_for_current_til = data.pop("tags", [])

            try:
                # Insert into tils table
                til_record = tils_table.insert(data, pk="id")
                til_id = til_record.last_pk # Get the auto-generated id for the TIL
                logging.info(f"Inserted TIL: '{data['title']}' with ID: {til_id}")

                # Process tags for this TIL
                if tags_for_current_til:
                    tag_ids_for_til = []
                    for tag_name in tags_for_current_til:
                        if not tag_name.strip(): # Skip empty tag names
                            logging.warning(f"Skipping empty tag for TIL ID {til_id}")
                            continue
                        try:
                            # Use lookup: inserts if not exists, returns PK (tag_id)
                            # This relies on 'tag_id' being the PK of the 'tags' table.
                            tag_id = tags_table.lookup({"name": tag_name.strip()}, pk="tag_id")
                            tag_ids_for_til.append(tag_id)
                        except Exception as e:
                            logging.error(f"Error looking up/inserting tag '{tag_name}' for TIL ID {til_id}: {e}")

                    # Insert into til_tags junction table
                    for tag_id in tag_ids_for_til:
                        try:
                            til_tags_table.insert({"til_id": til_id, "tag_id": tag_id}, pk=("til_id", "tag_id"), ignore=True)
                            # ignore=True in case of duplicate attempts, though pk should prevent it
                        except Exception as e:
                            logging.error(f"Error inserting into til_tags (til_id={til_id}, tag_id={tag_id}): {e}")
                    logging.info(f"  Associated tags for TIL ID {til_id}: {tags_for_current_til}")


                processed_count += 1
            except Exception as e:
                logging.error(f"Error inserting TIL data for '{data.get('title', 'Unknown Title')}' or its tags: {e}", exc_info=True)


    logging.info("-" * 20)
    logging.info(f"Finished processing. Inserted {processed_count} TIL entries and associated tags.")

    if processed_count == 0 and markdown_files:
        logging.warning("Processed markdown files but no valid entries were inserted. Check logs for errors.")
    elif processed_count == 0 and not markdown_files:
        logging.info("No markdown files to process.")


if __name__ == "__main__":
    main()