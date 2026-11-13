import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import spacy

from lit_corpse.populate_db import (
    LineRecord,
    get_db_connection,
    initialize_database,
    insert_records,
    parse_nlp_line,
    stream_corpus,
)


class TestIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])

    def test_parse_nlp_line_pos_tags(self):
        doc = self.nlp("The silent moon arose in golden mist.")
        record = parse_nlp_line(doc)
        self.assertIsNotNone(record)
        self.assertEqual(record.text, "The silent moon arose in golden mist.")
        self.assertEqual(record.start_pos, "DET")  # "The" is DET
        self.assertEqual(record.end_pos, "NOUN")  # "mist" is NOUN
        self.assertEqual(record.ends_punct, 1)  # ends with '.'

    def test_parse_nlp_line_punctuation_variations(self):
        # Line ending in semicolon
        doc1 = self.nlp("And weary wanderers rest awhile;")
        rec1 = parse_nlp_line(doc1)
        self.assertEqual(rec1.ends_punct, 1)

        # Line without terminal punctuation
        doc2 = self.nlp("Through endless valleys and winding streams")
        rec2 = parse_nlp_line(doc2)
        self.assertEqual(rec2.ends_punct, 0)

        # Line ending in exclamation mark and quote
        doc3 = self.nlp('She cried aloud, "Beware the night!"')
        rec3 = parse_nlp_line(doc3)
        self.assertEqual(rec3.ends_punct, 1)

    def test_parse_nlp_line_empty_or_punct_only(self):
        doc_punct = self.nlp("... --- ! ?")
        self.assertIsNone(parse_nlp_line(doc_punct))

        doc_spaces = self.nlp("   ")
        self.assertIsNone(parse_nlp_line(doc_spaces))

    def test_stream_corpus_filtering(self):
        with tempfile.NamedTemporaryFile(suffix=".ndjson.gz", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
                f.write(json.dumps({"s": "Too short"}) + "\n")  # 2 words -> filtered out
                f.write(json.dumps({"s": "Three words here"}) + "\n")  # 3 words -> keep
                f.write(json.dumps({"s": "This is a normal poetic line of poetry"}) + "\n")  # 8 words -> keep
                f.write(json.dumps({"s": " ".join(["word"] * 25)}) + "\n")  # 25 words -> filtered out

            lines = list(stream_corpus(tmp_path, min_words=3, max_words=20))
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0], "Three words here")
            self.assertEqual(lines[1], "This is a normal poetic line of poetry")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_database_init_and_insertion(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)

        try:
            initialize_database(db_path)
            with get_db_connection(db_path) as conn:
                cursor = conn.cursor()
                # Verify schema
                cursor.execute("PRAGMA table_info(lines)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
                self.assertIn("id", columns)
                self.assertIn("text", columns)
                self.assertIn("start_pos", columns)
                self.assertIn("end_pos", columns)
                self.assertIn("ends_punct", columns)

                # Verify indexes
                cursor.execute("PRAGMA index_list(lines)")
                index_names = [row[1] for row in cursor.fetchall()]
                self.assertIn("idx_start_pos", index_names)
                self.assertIn("idx_end_pos", index_names)
                self.assertIn("idx_ends_punct", index_names)

                # Test insertion
                records = [
                    LineRecord("Line one", "NOUN", "VERB", 0),
                    LineRecord("Line two.", "VERB", "NOUN", 1),
                ]
                total = insert_records(cursor, records, 0)
                self.assertEqual(total, 2)

                cursor.execute("SELECT COUNT(*) FROM lines")
                self.assertEqual(cursor.fetchone()[0], 2)
        finally:
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    unittest.main()
