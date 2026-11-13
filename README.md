# Exquisite Corpse Poetry Generator
---

Author: [R. Kyle Norris](mailto:r.kyle.norris@gmail.com)  
Status: Functional / Ready

---

## Summary

A Python CLI application that generates surrealist "Exquisite Corpse" poetry from a large corpus of public domain poetry lines. By pairing lightweight Part-of-Speech (POS) tagging with tunable syntactic randomness, the generator preserves grammatical flow across line breaks while allowing unexpected semantic juxtapositions.

## Features

- **Rule-Based POS Transition Map:** Maps trailing POS tags (`DET`, `ADJ`, `ADP`, `NOUN`, `PROPN`, `VERB`, `ADV`, `PRON`, `CCONJ`, `SCONJ`) to grammatically compatible start tags for the next line.
- **Terminal Punctuation Resets:** Resets transition restrictions to clause-starting tags (`SENTENCE_STARTERS`) whenever a line ends with `.`, `!`, `?`, or `;`.
- **Deterministic Decay Control (`--how-rotten`):** Allows blending between strict syntactic transitions (`0.0`) and chaotic random selection (`1.0`), using pre-calculated line corruption indices and automatic grammatical recovery.
- **Randomized Casing Modes:** Uniformly formats the poem across one of three casing styles:
  - `original`: Preserves raw corpus capitalization.
  - `lowercase`: Converts all lines to lowercase.
  - `sentence_case`: Capitalizes the first character of each line and lowercases the remainder.
- **Variable-Length Stanzas:** Chunks generated lines into stanzas of random lengths between 3 and 7 lines, with orphan control absorbing remainders smaller than 3 lines into the final stanza.
- **Deduplication & Resilient Fallbacks:** Ensures no duplicate line IDs appear within a single poem, with a multi-stage fallback chain to guarantee generation never fails.

## Installation & Setup

1. Install dependencies and the project:
   ```bash
   uv sync
   # or with pip:
   pip install -e .
   ```

2. Download the SpaCy model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Corpus & Database Ingestion

The application uses Allison Parrish's Gutenberg Poetry Corpus (`gutenberg-poetry-v001.ndjson.gz` or `gutenberg-poetry-corpus.ndjson.gz`).

To populate the local SQLite database (`poetry.db`):
```bash
# Ingest up to 100,000 lines (or omit --limit for the entire corpus)
python -m lit_corpse populate --db poetry.db --limit 100000
```

## CLI Usage

Run the poetry generator directly:
```bash
# Generate default 16-line poem with strict POS transitions
python -m lit_corpse

# Generate 20 lines with 50% syntactic decay
python -m lit_corpse -n 20 -r 0.5

# Specify custom database and casing mode
python -m lit_corpse --db poetry.db --lines 12 --how-rotten 0.0 --casing sentence_case
```

### CLI Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--db` | String | `poetry.db` | Path to the SQLite database. |
| `-n`, `--lines` | Integer | `16` | Total number of lines to generate. |
| `-r`, `--how-rotten` | Float | `0.0` | Syntactic decay/jitter factor ranging from `0.0` to `1.0`. |
| `--casing` | String | `None` (random) | Uniform casing mode (`original`, `lowercase`, `sentence_case`). |

## Running Tests

Run the full unit and integration test suite:
```bash
python -m unittest discover tests
```

## Source Information
- [Lines Source Info](https://github.com/aparrish/gutenberg-poetry-corpus)
- [Lines Source](http://static.decontextualize.com/gutenberg-poetry-v001.ndjson.gz)
