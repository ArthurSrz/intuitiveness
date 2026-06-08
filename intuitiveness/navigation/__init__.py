"""
Navigation Package

Phase 1.2 - Code Simplification (011-code-simplification)
Refactored from monolithic navigation.py (1,592 lines)

Package Structure:
------------------
- exceptions.py : NavigationError, SessionNotFoundError
- state.py      : NavigationState, NavigationAction enums
- tree.py       : NavigationTreeNode, NavigationTree (the navigation backbone)
- session.py    : NavigationSession (main class) [kept in original file]

Spec Traceability:
------------------
- 002-ascent-functionality: US-5 (Navigate Dataset Hierarchy)
- 004-ascent-precision: Domain categorization, linkage keys

Backward Compatibility:
-----------------------
All classes are re-exported here to maintain existing import patterns:
    from intuitiveness.navigation import NavigationSession, NavigationState
"""

# Re-export from submodules for backward compatibility
from intuitiveness.navigation.exceptions import (
    NavigationError,
    SessionNotFoundError,
)
from intuitiveness.navigation.state import (
    NavigationState,
    NavigationAction,
)
from intuitiveness.navigation.tree import (
    NavigationTreeNode,
    NavigationTree,
)

# Import NavigationSession from session module (011-code-simplification)
from intuitiveness.navigation.session import NavigationSession

__all__ = [
    # Exceptions
    'NavigationError',
    'SessionNotFoundError',

    # State enums
    'NavigationState',
    'NavigationAction',

    # Tree (branching)
    'NavigationTreeNode',
    'NavigationTree',

    # Session (main class)
    'NavigationSession',
]
