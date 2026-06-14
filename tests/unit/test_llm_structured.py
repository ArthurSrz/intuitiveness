"""Test that call_llm_structured validates LLM responses against Pydantic models."""

from unittest.mock import patch, MagicMock

import pytest

from intuitiveness.services.transition_models import (
    DomainSuggestion,
    ColumnSuggestion,
    AggregationSuggestion,
)
from intuitiveness.services.llm_client import call_llm_structured


def _mock_anthropic_tool_response(model_class, data: dict):
    """Simulate an Anthropic tool_use response block."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = data
    response = MagicMock()
    response.content = [block]
    return response


def _mock_openai_json_response(data: str):
    """Simulate an OpenAI chat completion with JSON content."""
    choice = MagicMock()
    choice.message.content = data
    response = MagicMock()
    response.choices = [choice]
    return response


class TestDomainSuggestionStructured:

    @patch("intuitiveness.services.llm_client._get_client")
    def test_anthropic_tool_use_returns_validated_model(self, mock_get):
        client = MagicMock()
        mock_get.return_value = ("anthropic", client)

        client.messages.create.return_value = _mock_anthropic_tool_response(
            DomainSuggestion,
            {
                "proposed_column": "score",
                "proposed_domains": ["low", "high"],
                "code": "df['category'] = pd.qcut(df['score'], 2, labels=['low','high']).astype(str)",
                "explanation": "Scores split at the median.",
            },
        )

        result = call_llm_structured("system", "user", DomainSuggestion)

        assert isinstance(result, DomainSuggestion)
        assert result.proposed_column == "score"
        assert result.proposed_domains == ["low", "high"]
        assert "category" in result.code

    @patch("intuitiveness.services.llm_client._get_client")
    def test_openai_json_schema_returns_validated_model(self, mock_get):
        import json
        client = MagicMock()
        mock_get.return_value = ("openai", client)

        client.chat.completions.create.return_value = _mock_openai_json_response(
            json.dumps({
                "proposed_column": "price",
                "proposed_domains": ["cheap", "expensive"],
                "code": "df['category'] = 'cheap'",
                "explanation": "Simple split.",
            })
        )

        result = call_llm_structured("system", "user", DomainSuggestion)

        assert isinstance(result, DomainSuggestion)
        assert result.proposed_column == "price"

    @patch("intuitiveness.services.llm_client._get_client")
    def test_missing_required_field_raises_validation_error(self, mock_get):
        import json
        client = MagicMock()
        mock_get.return_value = ("openai", client)

        client.chat.completions.create.return_value = _mock_openai_json_response(
            json.dumps({
                "proposed_column": "score",
                # missing: proposed_domains, code, explanation
            })
        )

        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            call_llm_structured("system", "user", DomainSuggestion)

    @patch("intuitiveness.services.llm_client._get_client")
    def test_no_api_key_raises_runtime_error(self, mock_get):
        mock_get.return_value = None

        with pytest.raises(RuntimeError, match="No LLM API key"):
            call_llm_structured("system", "user", DomainSuggestion)


class TestColumnSuggestionStructured:

    @patch("intuitiveness.services.llm_client._get_client")
    def test_column_suggestion_with_optional_filter(self, mock_get):
        client = MagicMock()
        mock_get.return_value = ("anthropic", client)

        client.messages.create.return_value = _mock_anthropic_tool_response(
            ColumnSuggestion,
            {
                "proposed_column": "temperature",
                "proposed_filter": "year > 2000",
                "code": "series = df.query('year > 2000')['temperature']",
                "explanation": "Temperature after 2000 is most relevant.",
            },
        )

        result = call_llm_structured("system", "user", ColumnSuggestion)

        assert isinstance(result, ColumnSuggestion)
        assert result.proposed_column == "temperature"
        assert result.proposed_filter == "year > 2000"

    @patch("intuitiveness.services.llm_client._get_client")
    def test_column_suggestion_without_filter(self, mock_get):
        client = MagicMock()
        mock_get.return_value = ("anthropic", client)

        client.messages.create.return_value = _mock_anthropic_tool_response(
            ColumnSuggestion,
            {
                "proposed_column": "value",
                "code": "series = df['value']",
                "explanation": "Only numeric column.",
            },
        )

        result = call_llm_structured("system", "user", ColumnSuggestion)

        assert isinstance(result, ColumnSuggestion)
        assert result.proposed_filter is None


class TestAggregationSuggestionStructured:

    @patch("intuitiveness.services.llm_client._get_client")
    def test_aggregation_with_preview(self, mock_get):
        client = MagicMock()
        mock_get.return_value = ("anthropic", client)

        client.messages.create.return_value = _mock_anthropic_tool_response(
            AggregationSuggestion,
            {
                "proposed_aggregation": "median",
                "code": "result = series.median()",
                "explanation": "Median is robust to outliers.",
                "preview_value": 42.5,
            },
        )

        result = call_llm_structured("system", "user", AggregationSuggestion)

        assert isinstance(result, AggregationSuggestion)
        assert result.proposed_aggregation == "median"
        assert result.preview_value == 42.5
