"""
Chinese-aware tokenizer for PostgreSQL full-text search.

Postgres' built-in `simple` / `english` FTS configs split on non-word
characters. Chinese text has no spaces, so a whole sentence collapses into a
single token and `plainto_tsquery` almost never matches. Installing pg_jieba /
zhparser fixes this at the DB layer, but those are C extensions that managed /
self-hosted Postgres often disallow — a poor fit for a product meant to be
deployed by customers.

Instead we segment in the application with jieba and store space-joined tokens
in `knowledge_chunk.search_tokens`. Then `to_tsvector('simple', search_tokens)`
sees proper word boundaries and matches a jieba-segmented query. No DB
extension required, works on any Postgres.

jieba is imported lazily and optionally: if it is not installed, we fall back to
returning the original text (i.e. the previous behaviour), so search degrades
rather than breaks.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_jieba = None
_jieba_tried = False


def _get_jieba():
    global _jieba, _jieba_tried
    if not _jieba_tried:
        _jieba_tried = True
        try:
            import jieba  # type: ignore

            jieba.setLogLevel(logging.WARNING)
            _jieba = jieba
        except Exception as e:  # pragma: no cover - import guard
            logger.warning("jieba not available, Chinese FTS degraded: %s", e)
            _jieba = None
    return _jieba


def tokenize_for_search(text: str) -> str:
    """Return a space-joined token string suitable for to_tsvector('simple', …).

    Uses jieba search-mode segmentation (finer granularity, better recall) when
    available; otherwise returns the input unchanged.
    """
    if not text:
        return ""
    jieba = _get_jieba()
    if jieba is None:
        return text
    tokens = [t.strip() for t in jieba.cut_for_search(text) if t.strip()]
    return " ".join(tokens) if tokens else text
