"""Command Line Interface (CLI) for lit-corpse."""

import argparse
import sys

from .formatting import VALID_CASING_MODES
from .generator import PoetryGenerator
from .logger import get_logger
from .populate_db.init_db import DEFAULT_DB_PATH
from .populate_db.parse_poetry import process_poetry_corpus_and_load_db

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the lit-corpse CLI."""
    parser = argparse.ArgumentParser(
        prog="lit-corpse",
        description="Surrealist Exquisite Corpse poetry generator with POS transitions and tunable decay.",
    )

    # Core CLI flags specified in project summary
    parser.add_argument(
        "--db",
        type=str,
        default=str(DEFAULT_DB_PATH),
        help=f"Path to the SQLite database (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "-n",
        "--lines",
        type=int,
        default=16,
        help="Total number of lines to generate (default: 16).",
    )
    parser.add_argument(
        "-r",
        "--how-rotten",
        type=float,
        default=0.0,
        help="Syntactic decay/jitter factor ranging from 0.0 to 1.0 (default: 0.0).",
    )
    parser.add_argument(
        "--casing",
        type=str,
        choices=VALID_CASING_MODES,
        default=None,
        help="Uniform casing mode ('original', 'lowercase', 'sentence_case'). Defaults to random choice.",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Optional subcommands")

    # Subcommand: populate
    populate_parser = subparsers.add_parser(
        "populate",
        help="Ingest and parse lines from Gutenberg poetry corpus into SQLite database.",
    )
    populate_parser.add_argument(
        "--db",
        type=str,
        default=str(DEFAULT_DB_PATH),
        help=f"Path to the SQLite database to populate (default: {DEFAULT_DB_PATH}).",
    )
    populate_parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to .ndjson.gz source dataset. If omitted, searches default locations.",
    )
    populate_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of lines to ingest.",
    )
    populate_parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Batch size for SpaCy and SQLite inserts (default: 5000).",
    )
    populate_parser.add_argument(
        "--no-reinit",
        action="store_true",
        help="Append to existing database instead of dropping and recreating.",
    )

    return parser


def run_generate(args: argparse.Namespace) -> int:
    """Execute poem generation and print formatted poem to stdout."""
    try:
        generator = PoetryGenerator(db_path=args.db)
        poem = generator.generate(
            num_lines=args.lines,
            how_rotten=args.how_rotten,
            casing_mode=args.casing,
        )
        print(poem.text)
        return 0
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n\n")
        sys.stderr.write("To populate the database from the poetry corpus, run:\n")
        sys.stderr.write(f"  lit-corpse populate --db {args.db}\n")
        return 1
    except ValueError as e:
        sys.stderr.write(f"Validation Error: {e}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"Unexpected Error: {e}\n")
        logger.exception("Generation failed with unexpected error.")
        return 3


def run_populate(args: argparse.Namespace) -> int:
    """Execute corpus ingestion into SQLite database."""
    try:
        total = process_poetry_corpus_and_load_db(
            gz_path=args.source,
            db_path=args.db,
            batch_size=args.batch_size,
            max_lines=args.limit,
            reinit=not args.no_reinit,
        )
        print(f"Successfully populated '{args.db}' with {total:,} lines.")
        return 0
    except Exception as e:
        sys.stderr.write(f"Ingestion Error: {e}\n")
        logger.exception("Corpus ingestion failed.")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "populate":
        return run_populate(args)

    return run_generate(args)


if __name__ == "__main__":
    sys.exit(main())
