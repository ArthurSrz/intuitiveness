"""
App Package

Implements Spec 011: Code Simplification
Main Streamlit application modules.

Structure:
- sidebar.py: Sidebar rendering and controls
- pages/: Page-specific rendering modules
  - upload.py: File upload & data.gouv.fr search
  - discovery.py: L4→L3 connection wizard
  - descent.py: L3→L0 workflow
  - export.py: Session export

All modules follow single-responsibility principle (<300 lines).
"""

__all__ = []
