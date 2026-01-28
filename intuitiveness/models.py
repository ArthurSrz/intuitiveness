"""Embedding and similarity service using local SentenceTransformer.

Uses intfloat/multilingual-e5-small for multilingual support (French, etc.)
with fast local batching.
"""
import numpy as np
from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity

# Model for semantic similarity - multilingual support
SIMILARITY_MODEL = "intfloat/multilingual-e5-small"

# Cached model instance (loaded once, reused)
_model = None


def _get_streamlit():
    """Get Streamlit if available, None otherwise."""
    try:
        import streamlit as st
        return st
    except ImportError:
        return None


def _get_model():
    """Get or load the SentenceTransformer model (cached)."""
    global _model
    st = _get_streamlit()

    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            if st:
                st.info(f"Loading model {SIMILARITY_MODEL}...")
            _model = SentenceTransformer(SIMILARITY_MODEL)
            if st:
                st.success("Model loaded!")
        except ImportError:
            if st:
                st.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            return None
    return _model


def get_batch_similarities(source_sentences: List[str], target_sentences: List[str]) -> Optional[np.ndarray]:
    """Get pairwise similarities between two lists of sentences.

    Uses local SentenceTransformer for fast batched encoding.

    Args:
        source_sentences: List of source sentences
        target_sentences: List of target sentences to compare against

    Returns:
        numpy array of shape (len(source_sentences), len(target_sentences)) with similarity scores,
        or None if model fails to load
    """
    if not source_sentences or not target_sentences:
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        # Show progress for encoding
        st.info(f"Encoding {len(source_sentences)} items...")

        # Encode all sources and targets in batches (fast!)
        source_embeddings = model.encode(
            source_sentences,
            convert_to_numpy=True,
            show_progress_bar=len(source_sentences) > 50
        )
        target_embeddings = model.encode(
            target_sentences,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        # Compute cosine similarity matrix
        similarities = cosine_similarity(source_embeddings, target_embeddings)

        st.success(f"Encoding complete!")
        return similarities

    except Exception as e:
        st.warning(f"Embedding error: {e}")
        return None


def get_sentence_similarity(source_sentence: str, sentences: List[str]) -> Optional[List[float]]:
    """Get similarity scores between source and target sentences.

    Args:
        source_sentence: The reference sentence to compare against
        sentences: List of sentences to compare with source

    Returns:
        List of similarity scores (0-1) for each sentence, or None if fails
    """
    if not sentences:
        return None

    result = get_batch_similarities([source_sentence], sentences)
    if result is None:
        return None

    return result[0].tolist()


def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """Get embeddings for texts.

    Args:
        texts: List of strings to encode

    Returns:
        numpy array of shape (len(texts), embedding_dim) or None if fails
    """
    if not texts:
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 50
        )
        return embeddings

    except Exception as e:
        st.warning(f"Embedding error: {e}")
        return None


# Backwards compatibility
def get_embedding_model():
    """Deprecated: Use get_embeddings() or get_batch_similarities() instead."""
    return _get_model()
