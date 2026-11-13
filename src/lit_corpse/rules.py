"""Rule-based Part-of-Speech (POS) transitions and clause starters for poetry generation."""

# Standard clause-starting POS tags when a line ends with terminal punctuation (or for seed line)
SENTENCE_STARTERS: list[str] = [
    "DET",
    "PRON",
    "NOUN",
    "PROPN",
    "ADJ",
    "ADV",
    "VERB",
    "ADP",
    "SCONJ",
    "CCONJ",
]

# Rule-Based POS Transition Map:
# Maps each trailing POS tag to grammatically compatible starting POS tags for the subsequent line.
TRANSITION_MAP: dict[str, list[str]] = {
    # Determiner (e.g., 'the', 'a', 'this') -> noun phrase continuations
    "DET": ["NOUN", "PROPN", "ADJ", "ADV", "NUM"],
    # Adjective (e.g., 'golden', 'dark') -> modified nouns, stacked adjectives, or conjunctions
    "ADJ": ["NOUN", "PROPN", "ADJ", "CCONJ"],
    # Adposition / Preposition (e.g., 'in', 'upon', 'through') -> prepositional object
    "ADP": ["DET", "NOUN", "PROPN", "ADJ", "PRON", "NUM"],
    # Noun (e.g., 'night', 'water') -> verbs, post-modifiers, prepositions, conjunctions
    "NOUN": ["VERB", "AUX", "ADP", "CCONJ", "ADV", "SCONJ", "PRON", "ADJ"],
    # Proper Noun (e.g., 'Rome', 'Helen') -> verbs, prepositions, conjunctions
    "PROPN": ["VERB", "AUX", "ADP", "CCONJ", "ADV", "SCONJ", "PRON"],
    # Verb (e.g., 'sang', 'wanders') -> direct/indirect objects, adverbials, dependent clauses
    "VERB": ["NOUN", "PROPN", "PRON", "ADV", "ADP", "DET", "ADJ", "PART", "SCONJ", "CCONJ"],
    # Adverb (e.g., 'slowly', 'brightly') -> verbs, adjectives, further adverbs
    "ADV": ["VERB", "AUX", "ADJ", "ADV", "ADP", "CCONJ"],
    # Pronoun (e.g., 'thou', 'she', 'they') -> predicates, auxiliaries, adverbs
    "PRON": ["VERB", "AUX", "ADV", "ADJ", "ADP", "NOUN"],
    # Coordinating Conjunction (e.g., 'and', 'but') -> coordinated clauses or constituents
    "CCONJ": ["NOUN", "PROPN", "PRON", "VERB", "AUX", "ADJ", "ADV", "DET", "ADP", "SCONJ"],
    # Subordinating Conjunction (e.g., 'while', 'because', 'if') -> subordinate clause subjects/adverbials
    "SCONJ": ["NOUN", "PROPN", "PRON", "DET", "ADJ", "ADV", "ADP"],
    # Auxiliary verbs (e.g., 'was', 'shall', 'is')
    "AUX": ["VERB", "ADJ", "ADV", "DET", "NOUN", "PROPN", "PRON", "ADP", "PART"],
    # Particles (e.g., 'to', 'not')
    "PART": ["VERB", "AUX", "ADV"],
    # Numerals
    "NUM": ["NOUN", "PROPN", "ADJ", "CCONJ"],
}


def get_compatible_starting_tags(trailing_pos: str | None, ends_punct: int = 0) -> list[str]:
    """Return the list of compatible starting POS tags for the subsequent line.

    Args:
        trailing_pos: The end_pos of the preceding line.
        ends_punct: Binary flag (1 if preceding line ended with terminal punctuation, else 0).

    Returns:
        list[str]: Compatible starting POS tags.
    """
    if ends_punct == 1 or trailing_pos is None:
        return list(SENTENCE_STARTERS)

    tags = TRANSITION_MAP.get(trailing_pos)
    if tags:
        return list(tags)

    # Fallback to sentence starters if unknown POS tag
    return list(SENTENCE_STARTERS)
