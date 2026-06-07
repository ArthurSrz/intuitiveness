"""T005 — SourceReference round-trip + optional-field validity (spec 015 FR-004/FR-005)."""

from datetime import datetime, timezone

from intuitiveness.complexity import ComplexityLevel
from intuitiveness.redesign.lineage import SourceReference


def _ref(**over):
    base = dict(
        operation_type="L2→L1",
        input_level=ComplexityLevel.LEVEL_2,
        output_level=ComplexityLevel.LEVEL_1,
        timestamp=datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc),
        parameters={"column": "score"},
        row_count_before=10,
        row_count_after=10,
    )
    base.update(over)
    return SourceReference(**base)


def test_roundtrip_without_optional_fields():
    ref = _ref()
    restored = SourceReference.from_dict(ref.to_dict())
    assert restored.operation_type == "L2→L1"
    assert restored.input_level == ComplexityLevel.LEVEL_2
    assert restored.output_level == ComplexityLevel.LEVEL_1
    assert restored.parameters == {"column": "score"}
    assert restored.id is None
    assert restored.source_data_hash is None
    assert restored.result_data_hash is None


def test_roundtrip_with_optional_fields():
    ref = _ref(id="abc-123", source_data_hash="deadbeef", result_data_hash="cafef00d")
    restored = SourceReference.from_dict(ref.to_dict())
    assert restored.id == "abc-123"
    assert restored.source_data_hash == "deadbeef"
    assert restored.result_data_hash == "cafef00d"


def test_optional_fields_absent_is_valid():
    # from_dict on a legacy dict (no optional keys) must not raise.
    legacy = {
        "operation_type": "L1→L0",
        "input_level": "LEVEL_1",
        "output_level": "LEVEL_0",
        "timestamp": "2026-06-07T12:00:00+00:00",
        "parameters": {},
    }
    restored = SourceReference.from_dict(legacy)
    assert restored.id is None
    assert restored.duration_ms == 0.0


def test_ascent_specifics_ride_in_parameters():
    ref = _ref(
        operation_type="L1→L2",
        input_level=ComplexityLevel.LEVEL_1,
        output_level=ComplexityLevel.LEVEL_2,
        parameters={"dimensions": ["region", "year"], "enrichment_function": "expand"},
    )
    restored = SourceReference.from_dict(ref.to_dict())
    assert restored.parameters["dimensions"] == ["region", "year"]
    assert restored.parameters["enrichment_function"] == "expand"
