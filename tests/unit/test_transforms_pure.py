"""T010 — Transform modules stay payload-pure; the engine is the sole constructor.

Spec 015 FR-007/FR-008: the unified ``Redesigner`` engine is the ONLY component
allowed to construct a ``LevelNDataset`` and stamp its lineage. Transform helper
modules must return raw payloads (``pd.Series`` / ``pd.DataFrame`` / ``nx.Graph``)
and never wrap them in a typed level dataset.

This is a *static* guard: we parse each module's AST and assert it contains zero
``LevelNDataset(...)`` construction calls. A static check (rather than a runtime
one) means a regression is caught even if the offending branch is never executed.

The legacy modules ``ascent/unfold.py``, ``ascent/graph_builder.py`` and
``ascent/enrich.py`` were deleted when the unified engine became the sole path;
this test also pins that they stay gone, so a stray dataset-constructing helper
cannot quietly reappear under those names.
"""

import ast
import importlib.util
from pathlib import Path

import pytest

# The transform modules the engine actually uses. Each must be payload-pure.
LIVE_TRANSFORM_MODULES = [
    "intuitiveness.ascent.enrichment",
    "intuitiveness.ascent.dimensions",
]

# Deleted legacy modules that used to construct datasets — must not return.
DELETED_LEGACY_MODULES = [
    "intuitiveness/ascent/unfold.py",
    "intuitiveness/ascent/graph_builder.py",
    "intuitiveness/ascent/enrich.py",
    "intuitiveness/descent/semantic_join.py",
]

LEVEL_DATASET_NAMES = {
    "Level0Dataset",
    "Level1Dataset",
    "Level2Dataset",
    "Level3Dataset",
    "Level4Dataset",
}


def _module_source_path(module_name: str) -> Path:
    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin, f"Cannot locate module {module_name}"
    return Path(spec.origin)


def _level_dataset_constructions(source: str) -> list[str]:
    """Return the names of any ``LevelNDataset(...)`` *call* nodes in the source.

    Only call expressions count — a bare name in a type annotation, an isinstance
    check, or a docstring is not a construction.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in LEVEL_DATASET_NAMES:
                found.append(name)
    return found


@pytest.mark.parametrize("module_name", LIVE_TRANSFORM_MODULES)
def test_live_transform_module_constructs_zero_datasets(module_name):
    source = _module_source_path(module_name).read_text(encoding="utf-8")
    constructions = _level_dataset_constructions(source)
    assert constructions == [], (
        f"{module_name} must be payload-pure but constructs {constructions}. "
        f"Only intuitiveness.redesign.engine may build LevelNDataset objects (FR-007)."
    )


@pytest.mark.parametrize("rel_path", DELETED_LEGACY_MODULES)
def test_legacy_dataset_constructing_module_stays_deleted(rel_path):
    repo_root = Path(__file__).resolve().parents[2]
    assert not (repo_root / rel_path).exists(), (
        f"{rel_path} was deleted because the engine is the sole constructor; "
        f"it must not be reintroduced (would bypass FR-007 lineage stamping)."
    )


def test_engine_is_a_constructor_positive_control():
    """Sanity: the guard would actually catch a construction — the engine has them."""
    source = _module_source_path("intuitiveness.redesign.engine").read_text(encoding="utf-8")
    constructions = _level_dataset_constructions(source)
    assert constructions, (
        "Expected the engine to construct LevelNDataset objects; if it does not, "
        "the AST guard above is not testing what we think it is."
    )
