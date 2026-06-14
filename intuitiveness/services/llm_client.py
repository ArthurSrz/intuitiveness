"""Shared LLM client for all suggester services.

Resolves API keys and provider in one place. Each service only needs to
pass its system prompt and user prompt — provider fallback, JSON
extraction, and model selection are handled here.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "anthropic/claude-sonnet-4"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def _get_client() -> Optional[tuple]:
    """Return (kind, client) or None if no API key is available."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic
            return ("anthropic", anthropic.Anthropic(api_key=anthropic_key))
        except ImportError:
            pass

    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("EMBEDDING_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return ("openai", OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ))


def _extract_json(content: str) -> str:
    """Strip markdown code fences from LLM response."""
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0]
    return content


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model_env_var: str | None = None,
) -> str:
    """Call an LLM and return the raw response text (JSON fences stripped).

    Args:
        system_prompt: the system message
        user_prompt: the user message
        model_env_var: optional env var name for model override (e.g. "DOMAIN_SUGGEST_MODEL")

    Returns:
        The LLM response text with code fences removed.

    Raises:
        RuntimeError: if no API key is configured.
    """
    client_tuple = _get_client()
    if client_tuple is None:
        raise RuntimeError("No LLM API key configured (ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY).")

    kind, client = client_tuple
    model = os.getenv(model_env_var, DEFAULT_MODEL) if model_env_var else DEFAULT_MODEL

    if kind == "anthropic":
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""

    return _extract_json(content)


def call_llm_parse_json(
    system_prompt: str,
    user_prompt: str,
    model_env_var: str | None = None,
) -> dict:
    """Call an LLM and parse the response as JSON.

    Returns an empty dict on parse failure (logged as warning).
    """
    raw = call_llm(system_prompt, user_prompt, model_env_var)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("LLM response is not valid JSON: %s — raw: %s", exc, raw[:200])
        return {}


def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    output_model: type,
    model_env_var: str | None = None,
):
    """Call an LLM and return a validated Pydantic model instance.

    Uses structured output (tool_use for Anthropic, json_schema for OpenAI)
    to constrain the LLM to produce exactly the right shape. Falls back to
    parse-and-validate if structured output isn't available.

    Args:
        system_prompt: the system message
        user_prompt: the user message
        output_model: a Pydantic BaseModel class defining the expected output
        model_env_var: optional env var name for model override

    Returns:
        An instance of output_model, validated.

    Raises:
        RuntimeError: if no API key is configured.
        ValidationError: if the LLM output doesn't match the schema after retries.
    """
    client_tuple = _get_client()
    if client_tuple is None:
        raise RuntimeError("No LLM API key configured.")

    kind, client = client_tuple
    model = os.getenv(model_env_var, DEFAULT_MODEL) if model_env_var else DEFAULT_MODEL
    schema = output_model.model_json_schema()

    if kind == "anthropic":
        tool_name = output_model.__name__
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{
                "name": tool_name,
                "description": f"Return the analysis result as a {tool_name}.",
                "input_schema": schema,
            }],
            tool_choice={"type": "tool", "name": tool_name},
        )
        for block in response.content:
            if block.type == "tool_use":
                return output_model.model_validate(block.input)
        raw = response.content[0].text if response.content else ""
    else:
        tool_name = output_model.__name__
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            tools=[{
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Return the analysis result as a {tool_name}.",
                    "parameters": schema,
                },
            }],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
        choice = response.choices[0]
        if choice.message.tool_calls:
            import json as _json
            args = _json.loads(choice.message.tool_calls[0].function.arguments)
            return output_model.model_validate(args)
        raw = choice.message.content or ""

    content = _extract_json(raw)
    return output_model.model_validate_json(content)
