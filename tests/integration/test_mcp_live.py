"""
Live Integration Tests for DataGouvMCPService
==============================================

Tests against the public MCP server at https://mcp.data.gouv.fr/mcp.
Requires internet connectivity.

Feature: 014-datagouv-mcp-search
"""

import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "myenv/lib/python3.11/site-packages")

from intuitiveness.services.datagouv_mcp import DataGouvMCPService


def test_is_available():
    """T029: MCP server should be reachable."""
    service = DataGouvMCPService(timeout=10)
    assert service.is_available(), "MCP server at mcp.data.gouv.fr should be reachable"
    service.close()


def test_search_vaccination():
    """T029: search_datasets('vaccination') should return results with valid DatasetInfo."""
    service = DataGouvMCPService(timeout=10)
    result = service.search_datasets("vaccination", page_size=5)

    assert len(result.datasets) > 0, "vaccination search should return results"
    assert result.total > 0, "total should be > 0"

    ds = result.datasets[0]
    assert ds.id, "dataset should have an id"
    assert ds.title, "dataset should have a title"
    assert ds.organization_name, "dataset should have an organization"

    service.close()


def test_sc001_resultats_scolaires_colleges():
    """T030/SC-001: 'résultats scolaires collèges' must return >= 5 results."""
    service = DataGouvMCPService(timeout=10)
    result = service.search_datasets("résultats scolaires collèges", page_size=10)

    assert len(result.datasets) >= 5, (
        f"SC-001 FAILED: expected >= 5 results for 'résultats scolaires collèges', "
        f"got {len(result.datasets)}"
    )

    service.close()


def test_sc002_search_under_3_seconds():
    """T031/SC-002: Search results should appear within 3 seconds."""
    service = DataGouvMCPService(timeout=10)
    service.is_available()  # Warm up connection

    start = time.time()
    result = service.search_datasets("éducation", page_size=10)
    elapsed = time.time() - start

    assert elapsed < 3.0, (
        f"SC-002 FAILED: search took {elapsed:.2f}s, expected < 3.0s"
    )
    assert len(result.datasets) > 0, "should return results"

    service.close()


if __name__ == "__main__":
    tests = [
        test_is_available,
        test_search_vaccination,
        test_sc001_resultats_scolaires_colleges,
        test_sc002_search_under_3_seconds,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    sys.exit(1 if failed > 0 else 0)
