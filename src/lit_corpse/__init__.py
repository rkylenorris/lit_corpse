"""Exquisite Corpse Poetry Generator."""

from .cli import main
from .formatting import apply_casing, chunk_stanzas, format_poem
from .generator import GeneratedPoem, PoemLine, PoetryGenerator, generate_poem
from .populate_db import (
    DEFAULT_DB_PATH,
    LineRecord,
    get_db_connection,
    initialize_database,
    process_poetry_corpus_and_load_db,
    resolve_db_path,
    resolve_gz_path,
    stream_corpus,
)
from .rules import SENTENCE_STARTERS, TRANSITION_MAP, get_compatible_starting_tags

__all__ = [
    "DEFAULT_DB_PATH",
    "GeneratedPoem",
    "LineRecord",
    "PoemLine",
    "PoetryGenerator",
    "SENTENCE_STARTERS",
    "TRANSITION_MAP",
    "apply_casing",
    "chunk_stanzas",
    "format_poem",
    "generate_poem",
    "get_compatible_starting_tags",
    "get_db_connection",
    "initialize_database",
    "main",
    "process_poetry_corpus_and_load_db",
    "resolve_db_path",
    "resolve_gz_path",
    "stream_corpus",
]
