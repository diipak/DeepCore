import re
from typing import List
from deepcore2.core.concepts.service import STOP_WORDS

def extract_search_keywords(query: str) -> List[str]:
    """
    Extract meaningful search keywords from a natural-language query or search string.
    Strips stopwords, punctuation, lowercases tokens, and deduplicates while preserving order.
    Falls back to raw tokens if all tokens match STOP_WORDS.
    """
    if not query or not query.strip():
        return []

    # Find alphanumeric tokens (including hyphens and underscores)
    tokens = re.findall(r'\b[a-zA-Z0-9_-]+\b', query.lower())
    if not tokens:
        return []

    # Filter out stop words
    keywords = []
    seen = set()
    for token in tokens:
        if token in STOP_WORDS:
            continue
        if token not in seen:
            seen.add(token)
            keywords.append(token)

    # Fallback: if stripping stop words removed everything, return deduplicated tokens
    if not keywords:
        fallback = []
        seen_fb = set()
        for token in tokens:
            if token not in seen_fb:
                seen_fb.add(token)
                fallback.append(token)
        return fallback

    return keywords
