"""Core Exquisite Corpse poetry generation engine.

Implements rule-based POS transitions, terminal punctuation resets,
deterministic decay control (--how-rotten), deduplication, and fallbacks
encapsulated within the PoetryGenerator class.
"""

import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .formatting import (
    VALID_CASING_MODES,
    apply_casing,
    chunk_stanzas,
    format_poem,
)
from .logger import get_logger
from .populate_db.init_db import get_db_connection, resolve_db_path
from .rules import SENTENCE_STARTERS, TRANSITION_MAP, get_compatible_starting_tags

logger = get_logger()


@dataclass
class PoemLine:
    """Represents a single line of poetry within a generated poem."""

    id: int
    text: str
    start_pos: str
    end_pos: str
    ends_punct: int
    is_rotten: bool = False


@dataclass
class GeneratedPoem:
    """Represents a fully generated and formatted Exquisite Corpse poem."""

    text: str
    lines: list[PoemLine]
    stanzas: list[list[str]]
    casing_mode: str
    rotten_indices: set[int]
    how_rotten: float

    def __str__(self) -> str:
        return self.text


class PoetryGenerator:
    """Surrealist Exquisite Corpse poetry generator using POS transitions and decay control."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        casing_mode: str | None = None,
        min_stanza_length: int = 3,
        max_stanza_length: int = 7,
    ) -> None:
        """Initialize the poetry generator.

        Args:
            db_path: Path to the SQLite database (defaults to poetry.db / data/poetry.db).
            casing_mode: Optional default casing mode ('original', 'lowercase', 'sentence_case').
            min_stanza_length: Minimum stanza length for formatting (default: 3).
            max_stanza_length: Maximum stanza length for formatting (default: 7).
        """
        self.db_path = resolve_db_path(db_path)
        self.default_casing = casing_mode
        self.min_stanza_length = min_stanza_length
        self.max_stanza_length = max_stanza_length

        self._min_id: int | None = None
        self._max_id: int | None = None
        self._total_lines: int | None = None

    def get_db_bounds(self, conn: sqlite3.Connection) -> tuple[int, int, int]:
        """Retrieve and cache minimum ID, maximum ID, and total count of lines in database.

        Args:
            conn: Active SQLite database connection.

        Returns:
            tuple[int, int, int]: (min_id, max_id, total_count)
        """
        if self._min_id is None or self._max_id is None or self._total_lines is None:
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(id), MAX(id), COUNT(id) FROM lines")
            row = cursor.fetchone()
            if not row or row[0] is None or row[2] == 0:
                raise ValueError("Database contains no lines. Please populate database first.")
            self._min_id, self._max_id, self._total_lines = row[0], row[1], row[2]

        return self._min_id, self._max_id, self._total_lines

    def fetch_random_line(
        self,
        conn: sqlite3.Connection,
        used_ids: set[int],
    ) -> PoemLine:
        """Select a random line from the database, avoiding used IDs where possible.

        Args:
            conn: Active SQLite connection.
            used_ids: Set of line IDs already chosen for the current poem.

        Returns:
            PoemLine: Selected line instance marked as rotten.
        """
        min_id, max_id, _ = self.get_db_bounds(conn)
        cursor = conn.cursor()
        attempts = 5

        for _ in range(attempts):
            start_id = random.randint(min_id, max_id)
            cursor.execute(
                "SELECT id, text, start_pos, end_pos, ends_punct FROM lines WHERE id >= ? LIMIT 20",
                (start_id,),
            )
            rows = cursor.fetchall()
            candidates = [r for r in rows if r[0] not in used_ids]
            if candidates:
                row = random.choice(candidates)
                return PoemLine(
                    id=row[0],
                    text=row[1],
                    start_pos=row[2],
                    end_pos=row[3],
                    ends_punct=row[4],
                    is_rotten=True,
                )

            # Wrap around if start_id was near the end
            cursor.execute(
                "SELECT id, text, start_pos, end_pos, ends_punct FROM lines WHERE id < ? LIMIT 20",
                (start_id,),
            )
            rows = cursor.fetchall()
            candidates = [r for r in rows if r[0] not in used_ids]
            if candidates:
                row = random.choice(candidates)
                return PoemLine(
                    id=row[0],
                    text=row[1],
                    start_pos=row[2],
                    end_pos=row[3],
                    ends_punct=row[4],
                    is_rotten=True,
                )

        # Fallback: grab any line from table
        cursor.execute(
            "SELECT id, text, start_pos, end_pos, ends_punct FROM lines ORDER BY RANDOM() LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("No lines available in database.")
        return PoemLine(
            id=row[0],
            text=row[1],
            start_pos=row[2],
            end_pos=row[3],
            ends_punct=row[4],
            is_rotten=True,
        )

    def fetch_line_with_pos(
        self,
        conn: sqlite3.Connection,
        allowed_tags: Sequence[str],
        used_ids: set[int],
    ) -> PoemLine:
        """Fetch a line whose start_pos is in allowed_tags, avoiding used IDs.

        Implements fallback chain:
          1. Candidate tags in allowed_tags (shuffled)
          2. SENTENCE_STARTERS fallback
          3. Pure random selection fallback

        Args:
            conn: Active SQLite connection.
            allowed_tags: List of compatible universal POS tags.
            used_ids: Set of already used line IDs.

        Returns:
            PoemLine: Selected line instance.
        """
        min_id, max_id, _ = self.get_db_bounds(conn)
        cursor = conn.cursor()
        shuffled_tags = list(allowed_tags)
        random.shuffle(shuffled_tags)

        for tag in shuffled_tags:
            start_id = random.randint(min_id, max_id)

            # Query using the (start_pos, id) index
            cursor.execute(
                "SELECT id, text, start_pos, end_pos, ends_punct FROM lines WHERE start_pos = ? AND id >= ? LIMIT 20",
                (tag, start_id),
            )
            rows = cursor.fetchall()
            candidates = [r for r in rows if r[0] not in used_ids]
            if candidates:
                row = random.choice(candidates)
                return PoemLine(
                    id=row[0],
                    text=row[1],
                    start_pos=row[2],
                    end_pos=row[3],
                    ends_punct=row[4],
                    is_rotten=False,
                )

            # Wrap around lookup
            cursor.execute(
                "SELECT id, text, start_pos, end_pos, ends_punct FROM lines WHERE start_pos = ? AND id < ? LIMIT 20",
                (tag, start_id),
            )
            rows = cursor.fetchall()
            candidates = [r for r in rows if r[0] not in used_ids]
            if candidates:
                row = random.choice(candidates)
                return PoemLine(
                    id=row[0],
                    text=row[1],
                    start_pos=row[2],
                    end_pos=row[3],
                    ends_punct=row[4],
                    is_rotten=False,
                )

        # Fallback 1: Try general SENTENCE_STARTERS
        if allowed_tags != SENTENCE_STARTERS:
            logger.debug("No lines matched transition tags; falling back to SENTENCE_STARTERS.")
            return self.fetch_line_with_pos(conn, SENTENCE_STARTERS, used_ids)

        # Fallback 2: Pure random selection
        logger.debug("No lines matched SENTENCE_STARTERS; falling back to random line.")
        return self.fetch_random_line(conn, used_ids)

    def generate(
        self,
        num_lines: int = 16,
        how_rotten: float = 0.0,
        casing_mode: str | None = None,
    ) -> GeneratedPoem:
        """Generate an Exquisite Corpse poem based on POS transitions and tunable decay.

        Args:
            num_lines: Total number of lines to assemble (default: 16).
            how_rotten: Decay factor from 0.0 (strict) to 1.0 (pure random) (default: 0.0).
            casing_mode: Optional casing mode ('original', 'lowercase', 'sentence_case').
                         If None, uses self.default_casing or randomly chooses.

        Returns:
            GeneratedPoem: Result containing formatted text, stanzas, and metadata.
        """
        if num_lines < 1:
            raise ValueError(f"num_lines must be at least 1, got {num_lines}")

        if not 0.0 <= how_rotten <= 1.0:
            raise ValueError(f"how_rotten must be between 0.0 and 1.0, got {how_rotten}")

        # Resolve casing mode
        selected_casing = casing_mode or self.default_casing
        if selected_casing is None:
            selected_casing = random.choice(VALID_CASING_MODES)
        elif selected_casing not in VALID_CASING_MODES:
            raise ValueError(
                f"Invalid casing mode '{selected_casing}'. Must be one of: {VALID_CASING_MODES}"
            )

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database '{self.db_path}' does not exist. Please initialize and populate it first."
            )

        # Deterministic Decay Control:
        # Pre-calculate exact line indices to corrupt using random.sample()
        num_rotten = int(round(how_rotten * num_lines))
        num_rotten = max(0, min(num_lines, num_rotten))
        rotten_indices = set(random.sample(range(num_lines), num_rotten))

        poem_lines: list[PoemLine] = []
        used_ids: set[int] = set()

        with get_db_connection(self.db_path) as conn:
            # Ensure DB bounds are cached/validated
            self.get_db_bounds(conn)

            for i in range(num_lines):
                is_rotten_index = i in rotten_indices

                if is_rotten_index:
                    # Rotten line: completely random line from corpus
                    line = self.fetch_random_line(conn, used_ids)
                    line.is_rotten = True
                else:
                    # Normal grammatical line:
                    if i == 0:
                        allowed_tags = SENTENCE_STARTERS
                    else:
                        prev_line = poem_lines[-1]
                        allowed_tags = get_compatible_starting_tags(
                            trailing_pos=prev_line.end_pos,
                            ends_punct=prev_line.ends_punct,
                        )

                    line = self.fetch_line_with_pos(conn, allowed_tags, used_ids)
                    line.is_rotten = False

                used_ids.add(line.id)
                poem_lines.append(line)

        # Apply uniform casing mode across lines
        raw_texts = [line.text for line in poem_lines]
        cased_texts = apply_casing(raw_texts, selected_casing)

        # Chunk into variable-length stanzas with orphan control
        stanzas = chunk_stanzas(
            cased_texts,
            min_length=self.min_stanza_length,
            max_length=self.max_stanza_length,
        )
        formatted_poem_text = format_poem(stanzas)

        return GeneratedPoem(
            text=formatted_poem_text,
            lines=poem_lines,
            stanzas=stanzas,
            casing_mode=selected_casing,
            rotten_indices=rotten_indices,
            how_rotten=how_rotten,
        )

    # Alias generate_poem to generate
    generate_poem = generate


def generate_poem(
    db_path: Path | str | None = None,
    num_lines: int = 16,
    how_rotten: float = 0.0,
    casing_mode: str | None = None,
) -> GeneratedPoem:
    """Convenience function to generate a poem using a PoetryGenerator instance."""
    generator = PoetryGenerator(db_path=db_path)
    return generator.generate(
        num_lines=num_lines,
        how_rotten=how_rotten,
        casing_mode=casing_mode,
    )
