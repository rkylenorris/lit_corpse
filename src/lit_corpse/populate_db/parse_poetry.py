import gzip
import json
import spacy
import sqlite3

from pathlib import Path
from spacy.tokens import Doc

DB_PATH = Path("data/poetry.db")
GZ_FILE_PATH = Path("data/gutenberg-poetry-corpus.ndjson.gz")

LineRecord = tuple[str, str, str, int]


# 3. Stream and Filter Raw Lines
def stream_raw_lines(file_path: Path, min_words: int = 3, max_words: int = 20):
    """Yield clean line strings from the compressed dataset."""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for raw_line in f:
            data = json.loads(raw_line)
            line_text = data.get("s", "").strip()

            # Filter out empty, very short, or excessively long lines
            words = line_text.split()
            if min_words <= len(words) <= max_words:
                yield line_text


def parse_nlp_line(doc: Doc) -> LineRecord | None:
    """Return indexed fields for a line, or None when it has no valid tokens."""
    valid_tokens = [token for token in doc if not token.is_punct and not token.is_space]
    if not valid_tokens:
        return None

    text = doc.text
    start_pos = valid_tokens[0].pos_
    end_pos = valid_tokens[-1].pos_
    ends_punct = 1 if text[-1] in {".", "!", "?", ";"} else 0

    return text, start_pos, end_pos, ends_punct


def insert_records(cursor: sqlite3.Cursor, records: list[LineRecord]) -> None:
    """Insert a batch of parsed line records."""
    cursor.executemany(
        "INSERT INTO lines (text, start_pos, end_pos, ends_punct) VALUES (?, ?, ?, ?)",
        records,
    )


def main():
    # 1. Initialize SQLite Database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        start_pos TEXT NOT NULL,
        end_pos TEXT NOT NULL,
        ends_punct INTEGER NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_start_pos ON lines(start_pos);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_end_pos ON lines(end_pos);")
    conn.commit()

    # 2. Load Lightweight SpaCy Model (Disable Unnecessary Pipelines)
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])

    # 4. Batch Process with SpaCy and Save to SQLite
    BATCH_SIZE = 5000
    line_generator = stream_raw_lines(GZ_FILE_PATH)

    records_to_insert = []
    total_processed = 0

    print("Processing lines into SQLite database...")

    # Process texts in batches via SpaCy pipeline
    for doc in nlp.pipe(line_generator, batch_size=BATCH_SIZE):
        record = parse_nlp_line(doc)
        if record is None:
            continue

        records_to_insert.append(record)

        if len(records_to_insert) >= BATCH_SIZE:
            insert_records(cursor, records_to_insert)
            conn.commit()
            total_processed += len(records_to_insert)
            print(f"Indexed {total_processed:,} lines...")
            records_to_insert.clear()

    # Final commit for remaining items
    if records_to_insert:
        insert_records(cursor, records_to_insert)
        conn.commit()
        total_processed += len(records_to_insert)

    conn.close()
    print(f"Finished! Total lines indexed in '{DB_PATH}': {total_processed:,}")


if __name__ == "__main__":
    main()