"""Formatting utilities for Exquisite Corpse poetry generation.

Includes randomized casing modes and variable-length stanza chunking with orphan control.
"""

import random
from typing import Sequence

CASING_ORIGINAL = "original"
CASING_LOWERCASE = "lowercase"
CASING_SENTENCE_CASE = "sentence_case"

VALID_CASING_MODES = [CASING_ORIGINAL, CASING_LOWERCASE, CASING_SENTENCE_CASE]


def format_sentence_case(text: str) -> str:
    """Capitalize the first character and lowercase the remainder of the line."""
    if not text:
        return ""
    return text[0].upper() + text[1:].lower()


def apply_casing(lines: Sequence[str], mode: str) -> list[str]:
    """Apply uniform casing rule across all lines of a poem.

    Args:
        lines: List of line strings.
        mode: One of 'original', 'lowercase', or 'sentence_case'.

    Returns:
        list[str]: Lines with uniform casing applied.
    """
    if mode == CASING_ORIGINAL:
        return list(lines)
    if mode == CASING_LOWERCASE:
        return [line.lower() for line in lines]
    if mode == CASING_SENTENCE_CASE:
        return [format_sentence_case(line) for line in lines]

    raise ValueError(f"Unknown casing mode '{mode}'. Expected one of: {VALID_CASING_MODES}")


def chunk_stanzas(
    lines: Sequence[str],
    min_length: int = 3,
    max_length: int = 7,
) -> list[list[str]]:
    """Chunk lines into stanzas of random lengths between min_length and max_length.

    Implements orphan control to absorb trailing remainders smaller than min_length
    into the final stanza.

    Args:
        lines: Sequence of poetry line strings.
        min_length: Minimum stanza length (default: 3).
        max_length: Maximum stanza length (default: 7).

    Returns:
        list[list[str]]: List of stanzas, where each stanza is a list of lines.
    """
    line_list = list(lines)
    total = len(line_list)
    if total == 0:
        return []

    # If total lines cannot even make two minimal stanzas, keep as single stanza
    if total <= max_length:
        return [line_list]

    stanzas: list[list[str]] = []
    idx = 0

    while idx < total:
        rem = total - idx

        # If remainder fits within maximum stanza size, check orphan constraints
        if rem <= max_length:
            if rem < min_length and stanzas:
                stanzas[-1].extend(line_list[idx:])
            else:
                stanzas.append(line_list[idx:])
            break

        # Remainder is > max_length. Choose a random chunk size in [min_length, max_length]
        # such that the remainder after this chunk is either 0 or >= min_length.
        valid_lengths = [
            k
            for k in range(min_length, max_length + 1)
            if (rem - k == 0) or (rem - k >= min_length)
        ]

        if not valid_lengths:
            # Fallback in case constraint cannot be met: take min_length or finish
            chunk_len = min(max_length, rem)
        else:
            chunk_len = random.choice(valid_lengths)

        stanzas.append(line_list[idx : idx + chunk_len])
        idx += chunk_len

    # Orphan-control post-check: absorb any trailing stanza with fewer than min_length lines
    if len(stanzas) > 1 and len(stanzas[-1]) < min_length:
        orphan = stanzas.pop()
        stanzas[-1].extend(orphan)

    return stanzas


def format_poem(stanzas: Sequence[Sequence[str]]) -> str:
    """Format stanzas into a clean poem string with blank lines separating stanzas."""
    return "\n\n".join("\n".join(stanza) for stanza in stanzas)
