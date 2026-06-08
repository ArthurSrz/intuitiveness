"""Embedding and similarity service via an OpenAI-compatible embeddings API.

The embedding model is called over HTTP (no local model download) so the work is
reproducible — a reviewer only needs an API key, not a multi-GB local model.

Configuration (read from st.secrets first, then environment), all optional:
  - EMBEDDING_API_KEY  (aliases: OPENROUTER_API_KEY, OPENAI_API_KEY)  -- required to embed
  - EMBEDDING_BASE_URL  default "https://openrouter.ai/api/v1" (OpenAI-compatible)
  - EMBEDDING_MODEL     default "openai/text-embedding-3-small"

Because the base URL + model are config-driven, the same code works against
OpenRouter, OpenAI, the HF router, or any OpenAI-compatible embeddings endpoint —
switch provider by changing a secret, no code change. If no key is configured the
functions return None and callers degrade gracefully (the semantic step is optional).
"""
import logging
import os
from typing import List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/text-embedding-3-small"

_client = None  # cached OpenAI-compatible client


def _get_streamlit():
    try:
        import streamlit as st
        return st
    except ImportError:
        return None


def _secret(*names: str) -> Optional[str]:
    """Resolve a config value from st.secrets first, then environment."""
    st = _get_streamlit()
    if st is not None:
        for n in names:
            try:
                if n in st.secrets:
                    return st.secrets[n]
            except Exception:
                pass
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def _embedding_config():
    return {
        "api_key": _secret("EMBEDDING_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"),
        "base_url": _secret("EMBEDDING_BASE_URL") or DEFAULT_BASE_URL,
        "model": _secret("EMBEDDING_MODEL") or DEFAULT_MODEL,
    }


def _get_client():
    """Get or build the cached OpenAI-compatible client. None if unconfigured."""
    global _client
    if _client is not None:
        return _client
    cfg = _embedding_config()
    if not cfg["api_key"]:
        logger.warning("No embedding API key configured "
                       "(set EMBEDDING_API_KEY / OPENROUTER_API_KEY in st.secrets or env).")
        return None
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed. Run: pip install openai")
        return None
    _client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    return _client


def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """Embed a list of texts via the configured API.

    Returns an array of shape (len(texts), dim), or None if unconfigured/failed.
    """
    if not texts:
        return None
    client = _get_client()
    if client is None:
        return None
    model = _embedding_config()["model"]
    try:
        resp = client.embeddings.create(model=model, input=list(texts))
        # Preserve input order (OpenAI-compatible responses include .index).
        items = sorted(resp.data, key=lambda d: getattr(d, "index", 0))
        return np.array([d.embedding for d in items], dtype=float)
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        logger.warning(f"Embedding API error: {e}")
        st = _get_streamlit()
        if st:
            st.warning(f"Embedding API error: {e}")
        return None


def get_batch_similarities(source_sentences: List[str],
                           target_sentences: List[str]) -> Optional[np.ndarray]:
    """Pairwise cosine similarities between two lists of sentences.

    Returns an array (len(source), len(target)) of scores, or None on failure.
    """
    if not source_sentences or not target_sentences:
        return None
    src = get_embeddings(list(source_sentences))
    tgt = get_embeddings(list(target_sentences))
    if src is None or tgt is None:
        return None
    try:
        return cosine_similarity(src, tgt)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Similarity error: {e}")
        return None


def get_sentence_similarity(source_sentence: str,
                            sentences: List[str]) -> Optional[List[float]]:
    """Similarity scores between one source sentence and a list of sentences."""
    if not sentences:
        return None
    result = get_batch_similarities([source_sentence], sentences)
    if result is None:
        return None
    return result[0].tolist()


# Backwards compatibility (deprecated): there is no local model object anymore.
def get_embedding_model():
    """Deprecated: embeddings are served via API. Use get_embeddings()."""
    return None
