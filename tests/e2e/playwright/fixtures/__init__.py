"""
Playwright E2E test fixtures.

Implements Spec 006: Test configuration and shared fixtures
"""

from .ascent_config import (
    AscentConfig,
    SCHOOLS_CONFIG,
    ADEME_CONFIG,
    ENERGY_CONFIG,
    ALL_CONFIGS,
    get_config,
    get_all_configs,
)

__all__ = [
    'AscentConfig',
    'SCHOOLS_CONFIG',
    'ADEME_CONFIG',
    'ENERGY_CONFIG',
    'ALL_CONFIGS',
    'get_config',
    'get_all_configs',
]
