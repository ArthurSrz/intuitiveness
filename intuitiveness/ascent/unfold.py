"""
L0→L1 Deterministic Unfolding Module

Implements Spec 004: FR-001-004 (L0→L1 Deterministic Unfolding)

Provides deterministic unfolding that displays the original vector from which
L0 was aggregated. Blocks unfolding if no parent vector exists.

Functions:
----------
- unfold_l0_to_l1: Main unfolding function with strict parent validation
- NoParentError: Exception raised when no parent vector exists

Example:
--------
>>> from intuitiveness.complexity import Level0Dataset, Level1Dataset
>>> import pandas as pd
>>>
>>> # Create L1 vector
>>> scores = pd.Series([85, 90, 78, 92, 88], name="school_scores")
>>> l1 = Level1Dataset(scores, name="school_scores")
>>>
>>> # Aggregate to L0
>>> mean_score = scores.mean()  # 88.6
>>> l0 = Level0Dataset(mean_score, parent_data=scores, aggregation_method="mean")
>>>
>>> # Unfold back to L1
>>> l1_restored = unfold_l0_to_l1(l0)
>>> assert len(l1_restored.get_data()) == 5  # Original 5 scores restored
"""

from typing import Optional
import pandas as pd

from complexity import Level0Dataset, Level1Dataset


class NoParentError(Exception):
    """
    Exception raised when L0→L1 unfolding is attempted without parent data.

    Implements Spec 004: FR-003 (Parent Validation)

    This enforces data integrity by preventing ambiguous unfolding operations.
    """
    pass


def unfold_l0_to_l1(
    datum: Level0Dataset,
    validate_parent: bool = True
) -> Level1Dataset:
    """
    Unfold L0 datum to L1 vector deterministically.

    Implements Spec 004: FR-001-004 (L0→L1 Deterministic Unfolding)

    This operation is deterministic: if the datum was created by aggregating
    a parent vector, this function returns that exact parent vector. The
    aggregation method (mean/sum/count) is displayed to the user.

    Architectural Decision (from refactoring plan):
    ------------------------------------------------
    We enforce **strict parent validation** (Option A) to maintain data integrity.
    If a datum lacks parent data, unfolding is blocked with NoParentError.

    This prevents:
    - Ambiguous unfolding (what should the vector contain?)
    - Loss of provenance (where did this datum come from?)
    - Inconsistent state (different unfolds producing different results)

    Parameters:
    -----------
    datum : Level0Dataset
        The L0 datum to unfold
    validate_parent : bool
        If True (default), raises NoParentError if no parent exists.
        If False, allows manual vector specification (not recommended).

    Returns:
    --------
    Level1Dataset
        The original vector from which the datum was aggregated

    Raises:
    -------
    NoParentError
        If datum has no parent_data and validate_parent=True
    TypeError
        If datum is not a Level0Dataset

    Example:
    --------
    >>> # School scores example (from scientific paper, test0 dataset)
    >>> import pandas as pd
    >>> school_scores = pd.Series([82, 95, 78, 91, 88] * 82, name="score")
    >>> mean_score = school_scores.mean()  # 86.8
    >>>
    >>> # Create datum with parent reference
    >>> datum = Level0Dataset(
    ...     value=mean_score,
    ...     parent_data=school_scores,
    ...     aggregation_method="mean"
    ... )
    >>>
    >>> # Unfold deterministically
    >>> restored_vector = unfold_l0_to_l1(datum)
    >>> print(f"Unfolded {len(restored_vector.get_data())} scores")
    >>> print(f"Aggregation method: {datum.aggregation_method}")
    >>> # Output: "Unfolded 410 scores"
    >>> #         "Aggregation method: mean"
    """
    if not isinstance(datum, Level0Dataset):
        raise TypeError(f"Expected Level0Dataset, got {type(datum).__name__}")

    # Strict parent validation (Option A: recommended)
    if validate_parent and not datum.has_parent:
        raise NoParentError(
            f"Cannot unfold datum '{datum.value}' to L1: no parent vector exists. "
            f"\\n\\nThis datum was not created by aggregating a vector, so there's "
            f"no original data to restore. To create a new vector from this datum, "
            f"use an enrichment function instead (L0→L1 enrichment).\\n\\n"
            f"Datum details:\\n"
            f"  - Value: {datum.value}\\n"
            f"  - Has parent: {datum.has_parent}\\n"
            f"  - Aggregation method: {datum.aggregation_method}"
        )

    # Get parent vector (series)
    parent_series = datum.parent_data

    if parent_series is None:
        # This should only happen if validate_parent=False
        raise NoParentError("parent_data is None but validation was disabled")

    # Create L1 dataset from parent series
    vector_name = parent_series.name if hasattr(parent_series, 'name') else "vector"

    l1 = Level1Dataset(parent_series, name=str(vector_name))

    # Attach metadata for UI display
    l1._metadata = {
        "unfolded_from": datum.value,
        "aggregation_method": datum.aggregation_method,
        "original_length": len(parent_series),
        "source_operation": f"Unfolded from L0 datum (aggregation: {datum.aggregation_method})"
    }

    return l1


def get_aggregation_info(datum: Level0Dataset) -> dict:
    """
    Get aggregation information for UI display.

    Returns dictionary with:
    - aggregation_method: "mean", "sum", etc.
    - original_length: Number of values aggregated (if known)
    - has_parent: Whether parent data exists

    Parameters:
    -----------
    datum : Level0Dataset
        The datum to inspect

    Returns:
    --------
    dict
        Aggregation information for display

    Example:
    --------
    >>> info = get_aggregation_info(datum)
    >>> print(f"Aggregated {info['original_length']} values using {info['aggregation_method']}")
    """
    info = {
        "aggregation_method": datum.aggregation_method,
        "has_parent": datum.has_parent,
        "value": datum.value,
    }

    if datum.has_parent and datum.parent_data is not None:
        info["original_length"] = len(datum.parent_data)
        info["can_unfold"] = True
    else:
        info["original_length"] = None
        info["can_unfold"] = False

    return info
