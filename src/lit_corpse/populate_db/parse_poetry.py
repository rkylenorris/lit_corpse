import gzip
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import spacy
from spacy.tokens import Doc

from ..logger import get_logger
from .init_db import (
    DEFAULT_DB_PATH,
    get_db_connection,
    initialize_database,
    resolve_db_path,
)

logger = get_logger()

DEFAULT_GZ_CANDIDATES = [
    Path("data/gutenberg-poetry-corpus.ndjson.gz"),
    Path("data/gutenberg-poetry-v001.ndjson.gz"),
    Path("gutenberg-poetry-corpus.ndjson.gz"),
    Path("gutenberg-poetry-v001.ndjson.gz"),
]


def resolve_gz_path(gz_path: Path | str | None = None) -> Path:
    """Find and return an existing gzip dataset path."""
    if gz_path is not None:
        path = Path(gz_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Specified corpus file '{gz_path}' does not exist.")

    for candidate in DEFAULT_GZ_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Poetry corpus not found. Looked in: "
        + ", ".join(str(p) for p in DEFAULT_GZ_CANDIDATES)
    )


@dataclass
class LineRecord:
    """Dataclass to hold parsed line information for database insertion.

    text: The raw poetic line string.
    start_pos: Universal POS tag of first non-punctuation token.
    end_pos: Universal POS tag of last non-punctuation token.
    ends_punct: Binary flag (1 if ending in '.', '!', '?', or ';', otherwise 0).
    """

    text: str
    start_pos: str
    end_pos: str
    ends_punct: int


def stream_corpus(
    file_path: Path | str,
    min_words: int = 3,
    max_words: int = 20,
    max_lines: int | None = None,
) -> Generator[str, None, None]:
    """Reads compressed poetry corpus and lazily yields valid line strings.

    Args:
        file_path: Path to the compressed NDJSON poetry corpus file (.ndjson.gz).
        min_words: Minimum number of words a line must have.
        max_words: Maximum number of words a line can have.
        max_lines: Optional maximum number of lines to yield (useful for testing/benchmarking).

    Yields:
        Clean line strings from the compressed dataset.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file '{path}' not found.")

    logger.debug(
        f"Reading compressed dataset '{path}' and filtering for lines with {min_words}-{max_words} words..."
    )

    yielded_count = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for raw_line in f:
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            line_text = data.get("s", "").strip()
            if not line_text:
                continue

            words = line_text.split()
            if min_words <= len(words) <= max_words:
                yield line_text
                yielded_count += 1
                if max_lines is not None and yielded_count >= max_lines:
                    break


def parse_nlp_line(doc: Doc) -> LineRecord | None:
    """Parse relevant information from NLP Doc object and text.

    Args:
        doc: SpaCy Doc object representing a single line of text.

    Returns:
        LineRecord | None: Information about the line for database insertion, or None if invalid.
    """
    valid_tokens = [t for t in doc if not t.is_punct and not t.is_space]
    if not valid_tokens:
        return None

    text = doc.text.strip()
    if not text:
        return None

    start_pos = valid_tokens[0].pos_
    end_pos = valid_tokens[-1].pos_

    # Binary flag (1 if ending in '.', '!', '?', or ';', otherwise 0)
    terminal_chars = {".", "!", "?", ";"}
    ends_punct = 0
    if text[-1] in terminal_chars:
        ends_punct = 1
    elif len(text) > 1 and text[-1] in {'"', "'", "”", "’", ")", "]"} and text[-2] in terminal_chars:
        ends_punct = 1

    return LineRecord(
        text=text,
        start_pos=start_pos,
        end_pos=end_pos,
        ends_punct=ends_punct,
    )


def _insert_records(cursor: sqlite3.Cursor, records: list[LineRecord]) -> None:
    """Insert a batch of parsed line records into the lines table."""
    cursor.executemany(
        "INSERT INTO lines (text, start_pos, end_pos, ends_punct) VALUES (?, ?, ?, ?)",
        [(r.text, r.start_pos, r.end_pos, r.ends_punct) for r in records],
    )


def insert_records(cursor: sqlite3.Cursor, records: list[LineRecord], total_inserted: int) -> int:
    """Insert records, commit db, and log running total.

    Args:
        cursor: SQLite cursor.
        records: Batch of LineRecord instances.
        total_inserted: Running count of inserted records.

    Returns:
        int: Updated total inserted count.
    """
    if not records:
        return total_inserted

    try:
        _insert_records(cursor, records)
    except sqlite3.Error as e:
        logger.error(f"Error inserting records into database: {e}")
        raise

    cursor.connection.commit()
    total_inserted += len(records)
    logger.info(f"Inserted {len(records)} records. Total: {total_inserted:,}")
    return total_inserted


def process_poetry_corpus_and_load_db(
    gz_path: Path | str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
    batch_size: int = 5000,
    max_lines: int | None = None,
    reinit: bool = True,
) -> int:
    """Stream compressed corpus, parse POS tags with SpaCy, and insert records into SQLite.

    Args:
        gz_path: Path to .ndjson.gz file (auto-detected if None).
        db_path: Path to target SQLite database.
        batch_size: Number of lines to process per SpaCy and SQLite batch.
        max_lines: Optional limit on the number of lines to ingest.
        reinit: If True, re-creates the database schema before ingesting.

    Returns:
        int: Total number of records successfully ingested.
    """
    target_gz = resolve_gz_path(gz_path)
    target_db = Path(db_path)

    if reinit:
        logger.info(f"Initializing database at '{target_db}'...")
        initialize_database(target_db)

    logger.info("Loading lightweight SpaCy model (en_core_web_sm)...")
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])

    logger.info(f"Streaming lines from '{target_gz}'...")
    line_generator = stream_corpus(target_gz, max_lines=max_lines)

    records_to_insert: list[LineRecord] = []
    total_processed = 0

    with get_db_connection(target_db) as conn:
        cursor = conn.cursor()

        for doc in nlp.pipe(line_generator, batch_size=batch_size):
            record = parse_nlp_line(doc)
            if record is None:
                continue

            records_to_insert.append(record)
            if len(records_to_insert) >= batch_size:
                total_processed = insert_records(cursor, records_to_insert, total_processed)
                records_to_insert.clear()

        if records_to_insert:
            total_processed = insert_records(cursor, records_to_insert, total_processed)
            records_to_insert.clear()

    logger.info(f"Finished ingestion! Total lines indexed: {total_processed:,}")
    return total_processed
