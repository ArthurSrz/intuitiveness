"""
TabPFN Wrapper with Fallback Logic

Provides a unified interface to TabPFN with automatic fallback:
1. Primary: tabpfn-client (cloud API, no GPU required)
2. Fallback: tabpfn local (requires GPU for optimal speed)

Both versions implement sklearn-compatible interface.
Includes timeout handling for graceful degradation.
"""

import logging
import signal
import functools
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional, Literal, Tuple, Any, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import numpy as np
import pandas as pd
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

# ============================================================================
# CRITICAL FIX FOR STREAMLIT CLOUD: Inject fake constants BEFORE tabpfn imports
# ============================================================================
# Problem: tabpfn_client modules import CACHE_DIR and compute derived constants
# (like CACHED_TOKEN_FILE) at module load time. Any post-import patching is too late.
#
# Solution: Use sys.modules to inject a fake constants module BEFORE any
# tabpfn_client modules are imported. This guarantees all imports see the patched path.
# ============================================================================

_cache_dir = Path(tempfile.gettempdir()) / "tabpfn_cache"
_cache_dir.mkdir(parents=True, exist_ok=True)

# Check if tabpfn_client.constants is already loaded
if "tabpfn_client.constants" in sys.modules:
    # Already loaded - patch it directly
    logger.warning(f"[INIT] tabpfn_client.constants already loaded - patching existing module")
    sys.modules["tabpfn_client.constants"].CACHE_DIR = _cache_dir
else:
    # Not loaded yet - inject a fake module
    logger.info(f"[INIT] Injecting fake tabpfn_client.constants module with CACHE_DIR={_cache_dir}")

    # Create fake constants module
    _fake_constants = ModuleType("tabpfn_client.constants")
    _fake_constants.CACHE_DIR = _cache_dir

    # Add ModelVersion enum (required by estimator.py)
    from enum import Enum
    class ModelVersion(str, Enum):
        V2 = "v2"
        V2_5 = "v2.5"
    _fake_constants.ModelVersion = ModelVersion

    # Inject into sys.modules BEFORE any tabpfn imports
    sys.modules["tabpfn_client.constants"] = _fake_constants
    logger.info(f"[INIT] Fake constants module injected successfully")

# NOW when tabpfn_client modules import, they'll get our fake constants
# No need to manually patch service_wrapper - it will import the patched CACHE_DIR

# The patching is now done at module level (above) BEFORE any imports

# Environment variable to control backend preference
# Set TABPFN_PREFER_LOCAL=1 to prefer local inference
# Set TABPFN_PREFER_LOCAL=0 to prefer cloud API (default - faster on most machines)
_PREFER_LOCAL_DEFAULT = os.environ.get("TABPFN_PREFER_LOCAL", "0") == "1"


class TabPFNTimeoutError(Exception):
    """Raised when TabPFN operation times out."""
    pass


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to a function.

    Uses ThreadPoolExecutor for cross-platform compatibility.

    Args:
        timeout_seconds: Maximum execution time.

    Returns:
        Decorated function.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    raise TabPFNTimeoutError(
                        f"{func.__name__} timed out after {timeout_seconds}s"
                    )
        return wrapper
    return decorator

# Backend availability flags
_TABPFN_CLIENT_AVAILABLE = False
_TABPFN_LOCAL_AVAILABLE = False

try:
    # Import TabPFN classes (CACHE_DIR already patched above at module level)
    from tabpfn_client import TabPFNClassifier as ClientClassifier
    from tabpfn_client import TabPFNRegressor as ClientRegressor
    import tabpfn_client
    _TABPFN_CLIENT_AVAILABLE = True
    logger.info(f"[INIT] TabPFN client available (cache at {_cache_dir})")

    # Auto-load token from Streamlit secrets, environment, or stored file

    _token = None

    # Priority 1: Check Streamlit secrets (for deployed apps)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'TABPFN_ACCESS_TOKEN' in st.secrets:
            _token = st.secrets['TABPFN_ACCESS_TOKEN']
            logger.info("TabPFN token loaded from Streamlit secrets")
        elif hasattr(st, 'secrets') and 'TABPFN_TOKEN' in st.secrets:
            _token = st.secrets['TABPFN_TOKEN']
            logger.info("TabPFN token loaded from Streamlit secrets")
    except (ImportError, FileNotFoundError, KeyError):
        # Streamlit not available or secrets not configured
        pass

    # Priority 2: Check .env file (for local development)
    if not _token:
        try:
            from dotenv import load_dotenv
            # Try to find .env in project root (up to 3 levels up from this file)
            current_dir = Path(__file__).parent
            for _ in range(4):  # Check current and up to 3 parent directories
                env_file = current_dir / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    logger.info(f"Loaded .env file from {env_file}")
                    break
                current_dir = current_dir.parent
        except ImportError:
            logger.debug("python-dotenv not installed, skipping .env file loading")

    # Priority 3: Check environment variable
    if not _token:
        _token = os.environ.get("TABPFN_ACCESS_TOKEN") or os.environ.get("TABPFN_TOKEN")
        if _token:
            logger.info("TabPFN token loaded from environment variable")

    # Priority 4: Check stored token file
    if not _token:
        _token_file = Path.home() / ".tabpfn" / "token"
        if _token_file.exists():
            try:
                _token = _token_file.read_text().strip()
                logger.info("TabPFN token loaded from ~/.tabpfn/token")
            except Exception as e:
                logger.warning(f"Failed to load TabPFN token from file: {e}")

    # Set the token if found
    if _token:
        # CRITICAL FIX: Use ServiceClient.authorize() directly to bypass file cache
        # The standard set_access_token() calls UserAuthenticationClient.set_token() which:
        #   1. Calls ServiceClient.authorize() (in-memory) ✓
        #   2. Writes token to CACHED_TOKEN_FILE (fails on read-only filesystem) ✗
        # By calling ServiceClient.authorize() directly, we skip the file write entirely.
        try:
            from tabpfn_client.config import ServiceClient, Config
            ServiceClient.authorize(_token)
            Config.is_initialized = True
            logger.info("TabPFN authenticated via ServiceClient.authorize() (no file cache)")
        except Exception as e:
            logger.warning(f"ServiceClient.authorize() failed: {e}")
            # Fallback: try the standard method (works on writable filesystems)
            try:
                tabpfn_client.set_access_token(_token)
                logger.info("TabPFN authenticated via set_access_token()")
            except PermissionError as perm_e:
                logger.warning(f"Cannot authenticate TabPFN (read-only filesystem): {perm_e}")
    else:
        logger.warning(
            "No TabPFN token found. Configure in one of these ways:\n"
            "  1. Streamlit secrets: .streamlit/secrets.toml\n"
            "  2. Environment file: .env\n"
            "  3. Environment variable: TABPFN_ACCESS_TOKEN\n"
            "  4. Token file: ~/.tabpfn/token"
        )
except ImportError:
    ClientClassifier = None
    ClientRegressor = None

try:
    from tabpfn import TabPFNClassifier as LocalClassifier
    from tabpfn import TabPFNRegressor as LocalRegressor
    _TABPFN_LOCAL_AVAILABLE = True
except ImportError:
    LocalClassifier = None
    LocalRegressor = None


class TabPFNWrapper:
    """
    Unified TabPFN interface with automatic backend selection.

    Tries tabpfn-client (cloud API) first, falls back to local tabpfn.
    Implements sklearn-compatible fit/predict interface.

    Attributes:
        task_type: "classification" or "regression"
        backend: Which backend is active ("client", "local", or None)
        model: The underlying TabPFN model instance
    """

    def __init__(
        self,
        task_type: Literal["classification", "regression"] = "classification",
        prefer_local: Optional[bool] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize TabPFN wrapper.

        Args:
            task_type: Type of prediction task.
            prefer_local: If True, try local TabPFN before cloud API.
                         Defaults to TABPFN_PREFER_LOCAL env var (default: True).
            timeout: Timeout in seconds for API calls.
        """
        self.task_type = task_type
        self.prefer_local = prefer_local if prefer_local is not None else _PREFER_LOCAL_DEFAULT
        self.timeout = timeout
        self.backend: Optional[str] = None
        self.model: Optional[Any] = None
        self._fitted = False

        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the appropriate TabPFN backend."""
        if self.prefer_local:
            backends = [("local", self._init_local), ("client", self._init_client)]
        else:
            backends = [("client", self._init_client), ("local", self._init_local)]

        for name, init_fn in backends:
            try:
                if init_fn():
                    self.backend = name
                    logger.info(f"TabPFN initialized with {name} backend")
                    return
            except Exception as e:
                logger.warning(f"Failed to initialize {name} backend: {e}")

        logger.error("No TabPFN backend available")
        raise RuntimeError(
            "No TabPFN backend available. Install tabpfn-client or tabpfn: "
            "pip install tabpfn-client"
        )

    def _init_client(self) -> bool:
        """Initialize tabpfn-client backend."""
        if not _TABPFN_CLIENT_AVAILABLE:
            return False

        try:
            if self.task_type == "classification":
                self.model = ClientClassifier()
            else:
                self.model = ClientRegressor()
            return True
        except PermissionError as e:
            logger.warning(f"tabpfn-client permission error (read-only filesystem): {e}")
            return False
        except Exception as e:
            logger.warning(f"tabpfn-client initialization failed: {e}")
            return False

    def _init_local(self) -> bool:
        """Initialize local tabpfn backend."""
        if not _TABPFN_LOCAL_AVAILABLE:
            return False

        try:
            if self.task_type == "classification":
                self.model = LocalClassifier()
            else:
                self.model = LocalRegressor()
            return True
        except Exception as e:
            logger.warning(f"Local tabpfn initialization failed: {e}")
            return False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TabPFNWrapper":
        """
        Fit the TabPFN model with timeout handling.

        Args:
            X: Training features (n_samples, n_features).
            y: Training labels (n_samples,).

        Returns:
            self for method chaining.

        Raises:
            TabPFNTimeoutError: If fitting exceeds timeout.
        """
        if self.model is None:
            raise RuntimeError("TabPFN backend not initialized")

        # Convert pandas to numpy if needed
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        try:
            self._fit_with_timeout(X, y)
            self._fitted = True
        except TabPFNTimeoutError:
            logger.warning(f"TabPFN fit timed out after {self.timeout}s")
            raise

        return self

    def _fit_with_timeout(self, X: np.ndarray, y: np.ndarray) -> None:
        """Internal fit with timeout using ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.model.fit, X, y)
            try:
                future.result(timeout=self.timeout)
            except FuturesTimeoutError:
                raise TabPFNTimeoutError(
                    f"TabPFN fit timed out after {self.timeout}s"
                )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class labels or regression values.

        Args:
            X: Features to predict (n_samples, n_features).

        Returns:
            Predictions (n_samples,).
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if isinstance(X, pd.DataFrame):
            X = X.values

        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities (classification only).

        Args:
            X: Features to predict (n_samples, n_features).

        Returns:
            Class probabilities (n_samples, n_classes).
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if self.task_type != "classification":
            raise ValueError("predict_proba only available for classification")

        if isinstance(X, pd.DataFrame):
            X = X.values

        return self.model.predict_proba(X)

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        Compute prediction score.

        Args:
            X: Test features.
            y: True labels.

        Returns:
            Accuracy for classification, R² for regression.
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        return self.model.score(X, y)


def get_tabpfn_model(
    task_type: Literal["classification", "regression"] = "classification",
    prefer_local: Optional[bool] = None,
) -> TabPFNWrapper:
    """
    Factory function to get a TabPFN model wrapper.

    Args:
        task_type: Type of prediction task.
        prefer_local: If True, prefer local TabPFN over cloud API.
                     Defaults to TABPFN_PREFER_LOCAL env var (default: True).

    Returns:
        Configured TabPFNWrapper instance.
    """
    if prefer_local is None:
        prefer_local = _PREFER_LOCAL_DEFAULT
    return TabPFNWrapper(task_type=task_type, prefer_local=prefer_local)


def is_tabpfn_available() -> Tuple[bool, str]:
    """
    Check if any TabPFN backend is available.

    Returns:
        Tuple of (available, backend_name).
    """
    if _TABPFN_CLIENT_AVAILABLE:
        return True, "client"
    if _TABPFN_LOCAL_AVAILABLE:
        return True, "local"
    return False, "none"


@dataclass
class APIConsumptionEstimate:
    """Estimate of TabPFN API consumption for quality assessment.

    TabPFN API cost formula per call:
        api_cost = max((train_rows + test_rows) * n_cols * n_estimators, 5000)

    Where n_estimators = 8 (TabPFN default).
    """

    # Dataset dimensions
    n_rows: int
    n_features: int
    n_classes: int

    # API call breakdown
    cv_calls: int  # 5-fold cross-validation
    feature_importance_calls: int  # Ablation study per feature
    shap_calls: int  # SHAP/permutation importance
    total_calls: int

    # TabPFN API cost (using actual formula)
    cost_per_cv_call: int  # max((train+test) * cols * 8, 5000)
    cost_per_ablation_call: int  # max((train+test) * (cols-1) * 8, 5000)
    total_cv_cost: int
    total_feature_importance_cost: int
    total_shap_cost: int
    total_api_cost: int  # Total consumption units

    # Data volume
    total_cells: int  # rows × features

    # Limits check (TabPFN optimal: ≤10,000 rows, ≤500 features, ≤10 classes)
    within_row_limit: bool
    within_feature_limit: bool
    within_class_limit: bool
    is_optimal: bool

    # Warnings
    warnings: List[str]

    def summary(self) -> str:
        """Human-readable summary of API consumption."""
        lines = [
            f"📊 **Dataset**: {self.n_rows:,} rows × {self.n_features} features",
            f"🏷️ **Target classes**: {self.n_classes}",
            f"",
            f"**TabPFN API Cost Formula**: `max((train_rows + test_rows) × cols × 8, 5000)`",
            f"",
            f"**API Calls & Cost Breakdown:**",
            f"  • Cross-validation (5-fold): {self.cv_calls} calls × {self.cost_per_cv_call:,} = **{self.total_cv_cost:,}**",
            f"  • Feature importance ({self.n_features}+1 ablations × 3 folds): {self.feature_importance_calls} calls = **{self.total_feature_importance_cost:,}**",
            f"  • SHAP analysis: ~{self.shap_calls} calls = **{self.total_shap_cost:,}**",
            f"",
            f"**Total API Cost**: ~{self.total_api_cost:,} units",
        ]

        if self.is_optimal:
            lines.append(f"\n✅ Dataset is within TabPFN optimal limits")
        else:
            lines.append(f"\n⚠️ **Warnings:**")
            for warning in self.warnings:
                lines.append(f"  • {warning}")

        return "\n".join(lines)


def estimate_api_consumption(
    n_rows: int,
    n_features: int,
    n_classes: int = 2,
    cv_folds: int = 5,
    importance_folds: int = 3,
    n_estimators: int = 8,
    task_type: Literal["classification", "regression", "auto"] = "auto",
) -> APIConsumptionEstimate:
    """
    Estimate TabPFN API consumption before running quality assessment.

    Uses the actual TabPFN API cost formula:
        api_cost = max((num_train_rows + num_test_rows) * num_cols * n_estimators, 5000)

    Args:
        n_rows: Number of rows in dataset.
        n_features: Number of feature columns.
        n_classes: Number of unique target values (only relevant for classification).
        cv_folds: Number of cross-validation folds (default: 5).
        importance_folds: Number of folds for feature importance (default: 3).
        n_estimators: TabPFN ensemble size (default: 8).
        task_type: "classification", "regression", or "auto" (infers from n_classes).

    Returns:
        APIConsumptionEstimate with breakdown of expected API usage.
    """
    # Auto-detect task type if not specified
    if task_type == "auto":
        # If >20 unique values, likely regression
        task_type = "regression" if n_classes > 20 else "classification"
    # TabPFN API cost formula: max((train_rows + test_rows) * cols * n_estimators, 5000)
    # In CV, train+test = all rows, so cost per call = max(n_rows * n_features * 8, 5000)

    def tabpfn_cost(rows: int, cols: int) -> int:
        """Calculate TabPFN API cost using official formula."""
        return max(rows * cols * n_estimators, 5000)

    # Calculate API calls
    cv_calls = cv_folds  # One fit per fold

    # Feature importance: (n_features + 1) ablation runs × importance_folds
    # +1 for baseline (all features)
    feature_importance_calls = (n_features + 1) * importance_folds

    # SHAP/permutation importance: roughly n_features × 2 evaluations
    shap_calls = n_features * 2

    total_calls = cv_calls + feature_importance_calls + shap_calls

    # Calculate costs using TabPFN formula
    # CV: each fold uses all rows but train/test split doesn't change total
    cost_per_cv_call = tabpfn_cost(n_rows, n_features)
    total_cv_cost = cv_calls * cost_per_cv_call

    # Feature importance ablation: each ablation removes 1 feature
    # Average cost (some calls have n_features, baseline; some have n_features-1)
    cost_per_ablation_call = tabpfn_cost(n_rows, max(n_features - 1, 1))
    total_feature_importance_cost = feature_importance_calls * cost_per_ablation_call

    # SHAP: similar to ablation
    total_shap_cost = shap_calls * cost_per_ablation_call

    # Total API cost
    total_api_cost = total_cv_cost + total_feature_importance_cost + total_shap_cost

    # Data volume
    total_cells = n_rows * n_features

    # Check TabPFN optimal limits
    within_row_limit = n_rows <= 10000
    within_feature_limit = n_features <= 500
    # Class limit only applies to classification
    within_class_limit = n_classes <= 10 if task_type == "classification" else True
    is_optimal = within_row_limit and within_feature_limit and within_class_limit

    # Generate warnings
    warnings = []
    if not within_row_limit:
        warnings.append(f"Dataset has {n_rows:,} rows (TabPFN optimal: ≤10,000). Consider sampling.")
    if not within_feature_limit:
        warnings.append(f"Dataset has {n_features} features (TabPFN optimal: ≤500). Consider feature selection.")
    # Only warn about classes for classification tasks
    if task_type == "classification" and not within_class_limit:
        warnings.append(f"Target has {n_classes} classes (TabPFN optimal: ≤10). Consider grouping rare classes.")

    return APIConsumptionEstimate(
        n_rows=n_rows,
        n_features=n_features,
        n_classes=n_classes,
        cv_calls=cv_calls,
        feature_importance_calls=feature_importance_calls,
        shap_calls=shap_calls,
        total_calls=total_calls,
        cost_per_cv_call=cost_per_cv_call,
        cost_per_ablation_call=cost_per_ablation_call,
        total_cv_cost=total_cv_cost,
        total_feature_importance_cost=total_feature_importance_cost,
        total_shap_cost=total_shap_cost,
        total_api_cost=total_api_cost,
        total_cells=total_cells,
        within_row_limit=within_row_limit,
        within_feature_limit=within_feature_limit,
        within_class_limit=within_class_limit,
        is_optimal=is_optimal,
        warnings=warnings,
    )
