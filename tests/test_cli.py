import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lit_corpse.cli import build_parser, main
from lit_corpse.populate_db import (
    LineRecord,
    get_db_connection,
    initialize_database,
    insert_records,
)


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = Path(cls.tmp_file.name)
        initialize_database(cls.db_path)

        records = [
            LineRecord("Morning awakes with golden light", "NOUN", "NOUN", 0),
            LineRecord("Rivers flow toward the sea.", "NOUN", "NOUN", 1),
            LineRecord("Silent winds whisper in the trees", "ADJ", "NOUN", 0),
            LineRecord("Night brings the quiet peace.", "NOUN", "NOUN", 1),
        ]
        with get_db_connection(cls.db_path) as conn:
            cursor = conn.cursor()
            insert_records(cursor, records, 0)

    @classmethod
    def tearDownClass(cls):
        if cls.db_path.exists():
            cls.db_path.unlink()

    def test_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.lines, 16)
        self.assertEqual(args.how_rotten, 0.0)
        self.assertEqual(args.db, "poetry.db")

    def test_parser_custom_flags(self):
        parser = build_parser()
        args = parser.parse_args(["--lines", "24", "-r", "0.75", "--db", "custom.db"])
        self.assertEqual(args.lines, 24)
        self.assertEqual(args.how_rotten, 0.75)
        self.assertEqual(args.db, "custom.db")

    def test_cli_generate_run(self):
        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = main(["--db", str(self.db_path), "-n", "4", "-r", "0.0"])
        self.assertEqual(exit_code, 0)
        output = f.getvalue().strip()
        self.assertGreater(len(output), 0)
        lines = [l for l in output.splitlines() if l.strip()]
        self.assertEqual(len(lines), 4)

    def test_cli_missing_database_error(self):
        err = io.StringIO()
        with redirect_stderr(err):
            exit_code = main(["--db", "nonexistent_db_12345.db"])
        self.assertEqual(exit_code, 1)
        self.assertIn("nonexistent_db_12345.db", err.getvalue())


if __name__ == "__main__":
    unittest.main()
