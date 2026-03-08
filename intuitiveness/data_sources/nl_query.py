"""
Natural Language Query Engine
==============================

Uses HuggingFace SmolLM3-3B for true natural language understanding
to query data.gouv.fr datasets.

Flow:
1. User asks question in natural language (French)
2. SmolLM3-3B extracts intent → generates search keywords + filters
3. Search data.gouv for relevant datasets
4. Query resource data with generated filters

Feature: 008-datagouv-mcp
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# HuggingFace model for NL understanding (OpenAI-compatible API)
# SmolLM3-3B-Instruct has no working provider on HF router (tested 2026-03).
# Qwen2.5-72B-Instruct is confirmed working via live API test.
# All routed through HF — no extra API key needed beyond HF_TOKEN.
HF_BASE_URL = "https://router.huggingface.co/v1"
HF_PROVIDERS = [
    "Qwen/Qwen2.5-72B-Instruct",   # Stage 1: primary (confirmed working)
    "Qwen/Qwen2.5-7B-Instruct",    # Stage 2: lighter fallback
]
HF_MODEL = HF_PROVIDERS[0]  # default for backward compat


@dataclass
class NLQueryResult:
    """Result of natural language query parsing."""
    keywords: List[str]
    filters: Dict[str, Any]
    intent: str  # 'search', 'query', 'aggregate'
    sql_hint: Optional[str] = None
    raw_response: str = ""


class NLQueryEngine:
    """
    Natural language query engine using SmolLM3-3B.

    Transforms French natural language questions into:
    - Search keywords for data.gouv
    - SQL-like filters for resource queries
    - Aggregation hints
    """

    def __init__(self, hf_token: Optional[str] = None):
        """
        Initialize the NL query engine.

        Args:
            hf_token: HuggingFace API token. If not provided,
                      looks for HF_TOKEN environment variable.
        """
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")

        # Try Streamlit secrets if no env var
        if not self.hf_token:
            try:
                import streamlit as st
                self.hf_token = st.secrets.get("HF_TOKEN")
            except:
                pass

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required. Set HF_TOKEN environment variable, "
                "add to .streamlit/secrets.toml, or pass hf_token parameter."
            )

    def _call_hf_api(self, prompt: str, max_tokens: int = 256) -> str:
        """Call HuggingFace via OpenAI-compatible API with 3-stage provider fallback."""
        import logging
        from openai import OpenAI

        logger = logging.getLogger(__name__)

        client = OpenAI(
            base_url=HF_BASE_URL,
            api_key=self.hf_token,
        )

        # 3-stage fallback: hf-inference → novita → sambanova
        last_error = None

        for model_id in HF_PROVIDERS:
            try:
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "Tu es un assistant d'analyse de données. Réponds uniquement au format structuré demandé, sans explication supplémentaire."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.1,  # Low for structured output
                )
                return completion.choices[0].message.content or ""
            except Exception as e:
                logger.info(f"Provider {model_id.split(':')[-1]} failed: {e}")
                last_error = e
                continue

        raise last_error

    def parse_query(self, user_query: str, schema: Optional[Dict] = None) -> NLQueryResult:
        """
        Parse a natural language query into structured components.

        Args:
            user_query: User's question in French
            schema: Optional schema of available columns (for SQL generation)

        Returns:
            NLQueryResult with keywords, filters, and intent
        """
        # Build prompt for SmolLM3
        schema_info = ""
        if schema:
            cols = ", ".join(schema.get("columns", [])[:20])  # Limit columns
            schema_info = f"\nColonnes disponibles: {cols}"

        prompt = f"""Tu es un assistant qui analyse des questions en français sur des données publiques.
Extrais les informations suivantes de la question:
1. MOTS_CLES: mots-clés pour rechercher des datasets (séparés par des virgules)
2. FILTRES: conditions de filtrage au format colonne=valeur
3. INTENTION: search (chercher datasets) ou query (interroger données) ou aggregate (calculer)
{schema_info}
Réponds UNIQUEMENT au format demandé, sans explication.

Question: {user_query}

MOTS_CLES:"""

        try:
            response = self._call_hf_api(prompt, max_tokens=512)  # More tokens for full response
            return self._parse_response(response, user_query)
        except Exception as e:
            # Fallback: extract simple keywords
            return self._fallback_parse(user_query, str(e))

    def _parse_response(self, response: str, original_query: str) -> NLQueryResult:
        """Parse the model's structured response."""
        import re

        # Clean <think>...</think> tags from response (including unclosed)
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'<think>.*', '', response, flags=re.DOTALL)  # Unclosed tag
        response = response.strip()

        keywords = []
        filters = {}
        intent = "search"
        sql_hint = None

        lines = response.strip().split("\n")
        current_section = "keywords"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("MOTS_CLES:") or current_section == "keywords":
                # Extract keywords
                if ":" in line:
                    kw_part = line.split(":", 1)[1].strip()
                else:
                    kw_part = line
                keywords.extend([k.strip() for k in kw_part.split(",") if k.strip()])
                current_section = "filters"

            elif line.startswith("FILTRES:"):
                # Extract filters
                filter_part = line.split(":", 1)[1].strip()
                for f in filter_part.split(","):
                    if "=" in f:
                        key, val = f.split("=", 1)
                        filters[key.strip()] = val.strip()
                current_section = "intent"

            elif line.startswith("INTENTION:"):
                intent_part = line.split(":", 1)[1].strip().lower()
                if "query" in intent_part:
                    intent = "query"
                elif "aggregate" in intent_part or "calcul" in intent_part:
                    intent = "aggregate"
                else:
                    intent = "search"

        # If no keywords extracted, use simple fallback
        if not keywords:
            return self._fallback_parse(original_query, "No keywords extracted")

        # Split compound keywords (e.g., "résultats scolaires collèges" -> 3 keywords)
        # This helps with data.gouv.fr's picky search
        split_keywords = []
        for kw in keywords:
            # Split on spaces if keyword has 3+ words
            words = kw.split()
            if len(words) >= 3:
                split_keywords.extend(words)
            else:
                split_keywords.append(kw)

        # Dedupe while preserving order
        seen = set()
        unique_keywords = []
        for k in split_keywords:
            k_lower = k.lower()
            if k_lower not in seen and len(k) > 2:
                seen.add(k_lower)
                unique_keywords.append(k)

        return NLQueryResult(
            keywords=unique_keywords if unique_keywords else keywords,
            filters=filters,
            intent=intent,
            sql_hint=sql_hint,
            raw_response=response
        )

    def _fallback_parse(self, query: str, error: str) -> NLQueryResult:
        """Fallback keyword extraction when model fails."""
        # Simple French stopword removal
        stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou',
            'qui', 'que', 'quoi', 'dont', 'où', 'quels', 'quelles', 'quel',
            'quelle', 'sont', 'est', 'sur', 'pour', 'dans', 'en', 'par',
            'avec', 'sans', 'plus', 'moins', 'très', 'bien', 'tous', 'tout',
            'cette', 'ces', 'ce', 'cet', 'mon', 'ma', 'mes', 'ton', 'ta',
            'ses', 'notre', 'nos', 'leur', 'leurs', 'je', 'tu', 'il', 'elle',
            'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se', 'y', 'ne',
            'pas', 'au', 'aux', 'à', 'a', 'ont', 'été', 'être', 'avoir',
            'fait', 'faire', 'comme', 'si', 'mais', 'car', 'donc', 'ni',
            'entre', 'vers', 'chez', 'aussi', 'même', 'autres', 'autre',
            'données', 'dataset', 'datasets', 'donnees', 'quelles'
        }

        # Extract words, remove stopwords
        words = query.lower().replace('?', '').replace(',', ' ').split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        # Keep unique, max 5
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)
                if len(unique_keywords) >= 5:
                    break

        return NLQueryResult(
            keywords=unique_keywords if unique_keywords else query.split()[:3],
            filters={},
            intent="search",
            raw_response=f"[Fallback mode: {error}]"
        )

    def generate_search_query(self, nl_result: NLQueryResult) -> str:
        """Generate a search query string from NL result."""
        return " ".join(nl_result.keywords)


def parse_french_query(query: str, hf_token: Optional[str] = None) -> NLQueryResult:
    """
    Convenience function to parse a French natural language query.

    Args:
        query: User's question in French
        hf_token: Optional HuggingFace token

    Returns:
        NLQueryResult with extracted keywords and intent
    """
    try:
        engine = NLQueryEngine(hf_token)
        return engine.parse_query(query)
    except ValueError:
        # No token - use fallback
        engine = NLQueryEngine.__new__(NLQueryEngine)
        engine.hf_token = None
        return engine._fallback_parse(query, "No HF token")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'NLQueryEngine',
    'NLQueryResult',
    'parse_french_query',
    'HF_MODEL',
    'HF_PROVIDERS',
]
