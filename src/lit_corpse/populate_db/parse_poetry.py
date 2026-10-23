import gzip
import json
import spacy
import sqlite3

from pathlib import Path
from dataclasses import dataclass

from spacy.tokens import Doc
from ..logger import get_logger
from .init_db import get_db_connection


logger = get_logger() # initialize logger for this module

GZ_FILE_PATH = Path("data/gutenberg-poetry-corpus.ndjson.gz")

@dataclass
class LineRecord:
    """
    Dataclass to hold parsed line information for database insertion.
    
    text: The text of the line.
    start_pos: The part-of-speech tag of the first valid token in the line.
    end_pos: The part-of-speech tag of the last valid token in the line.
    ends_punct: An integer flag indicating if the line ends with punctuation (1) or not (0).
    ends_terminal_punct: An integer flag indicating if the line ends with terminal punctuation (., !, ?) (1) or not (0).
    """
    text: str
    start_pos: str
    end_pos: str
    ends_punct: int
    ends_terminal_punct: int


# 3. Stream and Filter Raw Lines
def stream_corpus(file_path: Path, min_words: int = 3, max_words: int = 20):
    """Reads compressed poetry corpus and returns lines

    Args:
        file_path (Path): path to the compressed poetry corpus file (gzip format).
        min_words (int, optional): Minimum number of words a line must have. Defaults to 3.
        max_words (int, optional): Maximum number of words a line can have. Defaults to 20.

    Yields:
        str: Clean line strings from the compressed dataset.
    """


    logger.debug(f"Reading compressed dataset and filtering for lines with {min_words}-{max_words} words...")

    # Open the gzip file and read line by line
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for raw_line in f:
            # Parse JSON, extracting whitespace stripped line text
            data = json.loads(raw_line)
            line_text = data.get("s", "").strip()

            # Filter out empty, very short, or excessively long lines
            words = line_text.split()
            if min_words <= len(words) <= max_words:
                yield line_text


def parse_nlp_line(doc: Doc) -> LineRecord | None:
    """Parse relevant information from NLP Doc object and text

    Args:
        doc (Doc): spacy Doc object representing a single line of text.

    Returns:
        LineRecord | None: Information about the line for database insertion, or None if the line is invalid.
    """

    # Filter out punctuation and whitespace tokens
    valid_tokens = [token for token in doc if not token.is_punct and not token.is_space]
    if not valid_tokens:
        return None

    final_token = valid_tokens[-1]
    ends_punct = 1 if (final_token.is_punct or final_token.is_space) else 0
    
    # Extract relevant information from the SpaCy Doc object
    text = doc.text
    start_pos = valid_tokens[0].pos_
    end_pos = valid_tokens[-1].pos_
    ends_punct = 1 if (final_token.is_punct or final_token.is_space) else 0
    ends_terminal_punct = 1 if text[-1] in {".", "!", "?"} else 0

    # Create a LineRecord dataclass instance
    line_record = LineRecord(
        text=text,
        start_pos=start_pos,
        end_pos=end_pos,
        ends_punct=ends_punct,
        ends_terminal_punct=ends_terminal_punct,
    )

    return line_record


def _insert_records(cursor: sqlite3.Cursor, records: list[LineRecord]) -> None:
    """Insert a batch of parsed line records."""
    cursor.executemany(
        "INSERT INTO lines (text, start_pos, end_pos, ends_punct, ends_terminal_punct) VALUES (?, ?, ?, ?, ?)",
        [(r.text, r.start_pos, r.end_pos, r.ends_punct, r.ends_terminal_punct) for r in records],
    )

def insert_records(cursor: sqlite3.Cursor, records: list[LineRecord], total_inserted: int) -> int:
    """Insert records, commit db, and log running total

    Args:
        cursor (sqlite3.Cursor): db cursor to execute insert statements
        records (list[LineRecord]): records to insert into the database
        total_inserted (int): running total of records inserted so far

    Returns:
        int: Updated total of records inserted
    """
    if not records:
        logger.debug("No records to insert.")
        return total_inserted

    try:
        _insert_records(cursor, records)
    except sqlite3.Error as e:
        logger.error(f"Error inserting records into database: {e}")
        raise

    cursor.connection.commit()
    total_inserted += len(records)
    logger.info(f"Inserted {len(records)} new records into the database. Total inserted: {total_inserted}")
    return total_inserted


def process_poetry_corpus_and_load_db():
    """Streams compressed corpus, parses relavant information, and inserts records to DB
    """

    logger.info(f"Initializing NLP pipeline to process lines from '{GZ_FILE_PATH}'...")
    # Load Lightweight SpaCy Model (Disable Unnecessary Pipelines)
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])

    logger.info("Creating generator for raw lines from the compressed dataset...")
    BATCH_SIZE = 5000
    line_generator = stream_corpus(GZ_FILE_PATH)

    records_to_insert = []
    total_processed = 0

    logger.info("Processing lines into SQLite database...")
    
    # Batch Process with SpaCy and Save to SQLite
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Process texts in batches via SpaCy pipeline
        for doc in nlp.pipe(line_generator, batch_size=BATCH_SIZE):
            record = parse_nlp_line(doc)
            if record is None:
                continue

            records_to_insert.append(record)

            if len(records_to_insert) >= BATCH_SIZE:
                total_processed = insert_records(cursor, records_to_insert, total_processed)
                records_to_insert.clear()

    # Final commit for remaining items
        if records_to_insert:
            total_processed = insert_records(cursor, records_to_insert, total_processed)
            records_to_insert.clear()

    logger.info(f"Finished! Total lines indexed: {total_processed:,}")

