import unittest
from lit_corpse.rules import (
    SENTENCE_STARTERS,
    TRANSITION_MAP,
    get_compatible_starting_tags,
)


class TestRules(unittest.TestCase):
    def test_specified_pos_tags_in_transition_map(self):
        """Ensure all 10 specified trailing POS tags are present in the transition map."""
        required_tags = [
            "DET",
            "ADJ",
            "ADP",
            "NOUN",
            "PROPN",
            "VERB",
            "ADV",
            "PRON",
            "CCONJ",
            "SCONJ",
        ]
        for tag in required_tags:
            self.assertIn(tag, TRANSITION_MAP, f"Tag {tag} missing from TRANSITION_MAP")
            self.assertIsInstance(TRANSITION_MAP[tag], list)
            self.assertGreater(len(TRANSITION_MAP[tag]), 0)

    def test_sentence_starters(self):
        """Ensure SENTENCE_STARTERS has universal clause starting tags."""
        self.assertIn("NOUN", SENTENCE_STARTERS)
        self.assertIn("PRON", SENTENCE_STARTERS)
        self.assertIn("DET", SENTENCE_STARTERS)
        self.assertIn("VERB", SENTENCE_STARTERS)

    def test_terminal_punctuation_reset(self):
        """When ends_punct == 1, starting tags must reset to SENTENCE_STARTERS."""
        for trailing in ["NOUN", "VERB", "ADJ", "DET"]:
            res = get_compatible_starting_tags(trailing, ends_punct=1)
            self.assertEqual(res, SENTENCE_STARTERS)

    def test_transition_without_terminal_punct(self):
        """When ends_punct == 0, returns the transitions from TRANSITION_MAP."""
        res_noun = get_compatible_starting_tags("NOUN", ends_punct=0)
        self.assertEqual(res_noun, TRANSITION_MAP["NOUN"])

        res_det = get_compatible_starting_tags("DET", ends_punct=0)
        self.assertEqual(res_det, TRANSITION_MAP["DET"])

    def test_unknown_pos_fallback(self):
        """When trailing POS is None or unknown, falls back to SENTENCE_STARTERS."""
        self.assertEqual(get_compatible_starting_tags(None, ends_punct=0), SENTENCE_STARTERS)
        self.assertEqual(get_compatible_starting_tags("UNKNOWN_TAG", ends_punct=0), SENTENCE_STARTERS)


if __name__ == "__main__":
    unittest.main()
