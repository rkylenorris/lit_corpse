import tempfile
import unittest
from pathlib import Path

from lit_corpse.formatting import CASING_LOWERCASE, CASING_ORIGINAL, CASING_SENTENCE_CASE
from lit_corpse.generator import PoetryGenerator, generate_poem
from lit_corpse.populate_db import (
    LineRecord,
    get_db_connection,
    initialize_database,
    insert_records,
)
from lit_corpse.rules import SENTENCE_STARTERS, TRANSITION_MAP


class TestGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary test database with controlled lines and POS tags
        cls.tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = Path(cls.tmp_file.name)
        initialize_database(cls.db_path)

        # Populate a variety of sample lines for each POS tag
        sample_records = [
            # Starters
            LineRecord("The golden morning woke the hill", "DET", "NOUN", 0),
            LineRecord("A solitary wanderer stood alone,", "DET", "ADV", 0),
            LineRecord("Dark shadows lengthened on the grass.", "ADJ", "NOUN", 1),
            LineRecord("Silent waters reflect the sky.", "ADJ", "NOUN", 1),
            LineRecord("Under the stars we gathered flowers,", "ADP", "NOUN", 0),
            LineRecord("In the ancient forest deep,", "ADP", "ADJ", 0),
            LineRecord("Night brings the quiet peace;", "NOUN", "NOUN", 1),
            LineRecord("Rivers flow toward the sea", "NOUN", "NOUN", 0),
            LineRecord("Flowers bloom beneath the rain", "NOUN", "NOUN", 0),
            LineRecord("She sang a melody of old times.", "PRON", "NOUN", 1),
            LineRecord("He saw the shadows fall,", "PRON", "VERB", 0),
            LineRecord("And sorrow passed away like smoke", "CCONJ", "NOUN", 0),
            LineRecord("While winter kept the world asleep", "SCONJ", "ADJ", 0),
            LineRecord("Slowly the mist began to fade", "ADV", "VERB", 0),
            # Verbs
            LineRecord("Descends into the quiet vales", "VERB", "NOUN", 0),
            LineRecord("Embraces all the weary land.", "VERB", "NOUN", 1),
            LineRecord("Whispered secrets to the wind", "VERB", "NOUN", 0),
            # Adjectives
            LineRecord("Golden sunlight warms the stone", "ADJ", "NOUN", 0),
            LineRecord("Bitter cold and barren trees", "ADJ", "NOUN", 0),
            # Prepositions
            LineRecord("Through the dark and narrow gate", "ADP", "NOUN", 0),
            LineRecord("Upon the mountain high and wild", "ADP", "ADJ", 0),
            # Conjunctions
            LineRecord("Or listened to the midnight chime.", "CCONJ", "NOUN", 1),
            LineRecord("Because the earth remembers all.", "SCONJ", "DET", 1),
        ]

        with get_db_connection(cls.db_path) as conn:
            cursor = conn.cursor()
            insert_records(cursor, sample_records, 0)

        cls.generator = PoetryGenerator(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        if cls.db_path.exists():
            cls.db_path.unlink()

    def test_class_instantiation_and_bounds_caching(self):
        """Ensure PoetryGenerator caches db bounds properly."""
        with get_db_connection(self.db_path) as conn:
            min_id, max_id, count = self.generator.get_db_bounds(conn)
            self.assertEqual(min_id, 1)
            self.assertEqual(count, 23)
            self.assertGreaterEqual(max_id, 23)

    def test_fetch_random_line_method(self):
        """Test fetch_random_line method on generator instance."""
        with get_db_connection(self.db_path) as conn:
            line = self.generator.fetch_random_line(conn, used_ids=set())
            self.assertIsNotNone(line)
            self.assertTrue(line.is_rotten)

    def test_fetch_line_with_pos_method(self):
        """Test fetch_line_with_pos method on generator instance."""
        with get_db_connection(self.db_path) as conn:
            line = self.generator.fetch_line_with_pos(conn, allowed_tags=["NOUN"], used_ids=set())
            self.assertIsNotNone(line)
            self.assertEqual(line.start_pos, "NOUN")
            self.assertFalse(line.is_rotten)

    def test_deduplication(self):
        """Ensure no line ID is repeated within a generated poem."""
        poem = self.generator.generate(num_lines=16, how_rotten=0.0)
        line_ids = [line.id for line in poem.lines]
        self.assertEqual(len(line_ids), 16)
        self.assertEqual(len(set(line_ids)), 16, "Duplicate line IDs detected!")

    def test_decay_control_zero(self):
        """how_rotten = 0.0 must have 0 rotten lines."""
        poem = self.generator.generate(num_lines=16, how_rotten=0.0)
        self.assertEqual(len(poem.rotten_indices), 0)
        for line in poem.lines:
            self.assertFalse(line.is_rotten)

    def test_decay_control_one(self):
        """how_rotten = 1.0 must have all lines marked rotten."""
        poem = self.generator.generate(num_lines=16, how_rotten=1.0)
        self.assertEqual(len(poem.rotten_indices), 16)
        for line in poem.lines:
            self.assertTrue(line.is_rotten)

    def test_decay_control_partial(self):
        """how_rotten = 0.5 with 16 lines must have exactly 8 rotten lines."""
        poem = self.generator.generate(num_lines=16, how_rotten=0.5)
        self.assertEqual(len(poem.rotten_indices), 8)
        rotten_count = sum(1 for line in poem.lines if line.is_rotten)
        self.assertEqual(rotten_count, 8)

    def test_first_line_uses_sentence_starters(self):
        """The first line of a non-rotten poem must use a sentence starter."""
        for _ in range(5):
            poem = self.generator.generate(num_lines=4, how_rotten=0.0)
            first_line = poem.lines[0]
            self.assertIn(first_line.start_pos, SENTENCE_STARTERS)

    def test_grammatical_recovery_after_rotten_line(self):
        """A line following a rotten line recovers grammar based on the rotten line's end_pos."""
        for _ in range(10):
            poem = self.generator.generate(num_lines=10, how_rotten=0.3)
            for i in range(1, len(poem.lines)):
                prev = poem.lines[i - 1]
                curr = poem.lines[i]
                if prev.is_rotten and not curr.is_rotten:
                    if prev.ends_punct == 1:
                        self.assertIn(
                            curr.start_pos,
                            SENTENCE_STARTERS,
                            f"Line after terminal punct did not reset to SENTENCE_STARTERS: {curr.start_pos}",
                        )
                    else:
                        expected = TRANSITION_MAP.get(prev.end_pos, SENTENCE_STARTERS)
                        self.assertTrue(
                            curr.start_pos in expected or curr.start_pos in SENTENCE_STARTERS,
                            f"Recovery failed: {curr.start_pos} not compatible with {prev.end_pos}",
                        )

    def test_casing_mode_applied(self):
        poem_lower = self.generator.generate(
            num_lines=6, how_rotten=0.0, casing_mode=CASING_LOWERCASE
        )
        self.assertEqual(poem_lower.casing_mode, CASING_LOWERCASE)
        for stanza in poem_lower.stanzas:
            for line in stanza:
                self.assertEqual(line, line.lower())

        poem_sentence = self.generator.generate(
            num_lines=6, how_rotten=0.0, casing_mode=CASING_SENTENCE_CASE
        )
        self.assertEqual(poem_sentence.casing_mode, CASING_SENTENCE_CASE)
        for stanza in poem_sentence.stanzas:
            for line in stanza:
                if line:
                    self.assertTrue(line[0].isupper(), f"Line does not start uppercase: {line}")
                    self.assertEqual(line[1:], line[1:].lower())

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            self.generator.generate(num_lines=0)
        with self.assertRaises(ValueError):
            self.generator.generate(how_rotten=-0.1)
        with self.assertRaises(ValueError):
            self.generator.generate(how_rotten=1.5)

    def test_generate_poem_function_compatibility(self):
        """Test top-level generate_poem backward-compatibility helper."""
        poem = generate_poem(db_path=self.db_path, num_lines=4, how_rotten=0.0)
        self.assertEqual(len(poem.lines), 4)


if __name__ == "__main__":
    unittest.main()
