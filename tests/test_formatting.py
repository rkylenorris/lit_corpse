import unittest
from lit_corpse.formatting import (
    CASING_LOWERCASE,
    CASING_ORIGINAL,
    CASING_SENTENCE_CASE,
    apply_casing,
    chunk_stanzas,
    format_poem,
)


class TestFormatting(unittest.TestCase):
    def test_casing_original(self):
        lines = ["The Woods are Lovely, Dark and Deep,", "And I have PROMISES to keep."]
        result = apply_casing(lines, CASING_ORIGINAL)
        self.assertEqual(result, lines)

    def test_casing_lowercase(self):
        lines = ["The Woods are Lovely, Dark and Deep,", "And I have PROMISES to keep."]
        expected = ["the woods are lovely, dark and deep,", "and i have promises to keep."]
        self.assertEqual(apply_casing(lines, CASING_LOWERCASE), expected)

    def test_casing_sentence_case(self):
        lines = ["tHE WOODS ARE LOVELY,", "and I have PROMISES TO KEEP."]
        expected = ["The woods are lovely,", "And i have promises to keep."]
        self.assertEqual(apply_casing(lines, CASING_SENTENCE_CASE), expected)

    def test_invalid_casing_mode(self):
        with self.assertRaises(ValueError):
            apply_casing(["line"], "invalid_mode")

    def test_chunk_stanzas_orphan_control(self):
        """Verify stanzas are between 3 and 7 lines, and no trailing stanza < 3 remains."""
        for total_lines in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 25, 33]:
            lines = [f"Line {i}" for i in range(total_lines)]
            stanzas = chunk_stanzas(lines, min_length=3, max_length=7)

            # Flattened lines must match original
            flattened = [line for stanza in stanzas for line in stanza]
            self.assertEqual(flattened, lines)

            # Check stanza lengths
            if total_lines >= 3:
                for idx, stanza in enumerate(stanzas):
                    self.assertGreaterEqual(
                        len(stanza),
                        3,
                        f"Stanza {idx} has {len(stanza)} lines for total {total_lines}",
                    )
            else:
                self.assertEqual(len(stanzas), 1)

    def test_chunk_stanzas_edge_cases(self):
        # Empty
        self.assertEqual(chunk_stanzas([]), [])
        # Very short (less than min_length)
        self.assertEqual(chunk_stanzas(["L1"]), [["L1"]])
        self.assertEqual(chunk_stanzas(["L1", "L2"]), [["L1", "L2"]])

    def test_format_poem(self):
        stanzas = [["Line 1", "Line 2"], ["Line 3", "Line 4"]]
        expected = "Line 1\nLine 2\n\nLine 3\nLine 4"
        self.assertEqual(format_poem(stanzas), expected)


if __name__ == "__main__":
    unittest.main()
