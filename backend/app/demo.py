"""Demo dataset loader — mirrors the Streamlit app's demo placeholders.

Each demo is a single L4 (UNLINKABLE) dataset. The reference 'School Scores' set
is id 1..10 / value 10..100, whose mean is 55 — the canonical descent result.
"""

from __future__ import annotations

import pandas as pd

from intuitiveness.complexity import Level4Dataset

# name -> (title, builder) ; builder returns a {filename: DataFrame} dict
_DEMOS = {
    "school_scores": (
        "School Scores",
        lambda: {"School Scores": pd.DataFrame(
            {"id": range(1, 11), "value": [i * 10 for i in range(1, 11)]}
        )},
    ),
    "ademe": (
        "ADEME Funding",
        lambda: {"ADEME Funding": pd.DataFrame(
            {"recipient": [f"org_{i}" for i in range(1, 11)],
             "amount": [i * 1000 for i in range(1, 11)]}
        )},
    ),
    "energy": (
        "Energy Prices",
        lambda: {"Energy Prices": pd.DataFrame(
            {"country": [f"c_{i}" for i in range(1, 11)],
             "price": [i * 5 for i in range(1, 11)]}
        )},
    ),
}


def available_demos() -> list[dict]:
    return [{"id": key, "title": title} for key, (title, _) in _DEMOS.items()]


def load_demo(source: str) -> Level4Dataset:
    """Build an L4 dataset from a 'demo:<key>' source string."""
    key = source.split(":", 1)[1] if source.startswith("demo:") else source
    if key not in _DEMOS:
        raise KeyError(f"Unknown demo dataset '{key}'. Available: {list(_DEMOS)}")
    _title, builder = _DEMOS[key]
    return Level4Dataset(builder())
