"""
Integration test: data.gouv.fr MCP + World Bank API imports
============================================================

Verifies that both external data sources can be fetched and turned
into live Level4 sessions via the SessionService.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from backend.app.service import SessionService
from intuitiveness.persistence.durable_backend import FileDurableBackend


def make_svc(tmp_path: Path) -> SessionService:
    return SessionService(backend=FileDurableBackend(tmp_path))


# ──────────────────────────────────────────────────────────────────────────────
# data.gouv.fr MCP
# ──────────────────────────────────────────────────────────────────────────────

def test_datagouv_mcp_search_and_import(tmp_path):
    """MCP search returns at least one result; first CSV resource downloads OK."""
    from intuitiveness.services.datagouv_mcp import DataGouvMCPService

    mcp = DataGouvMCPService()
    if not mcp.is_available():
        pytest.skip("data.gouv.fr MCP not reachable")

    result = mcp.search_datasets("college résultats brevet", page_size=5)
    assert len(result.datasets) > 0, "MCP search returned no datasets"

    # Find first dataset that has CSV resources
    csv_df: pd.DataFrame | None = None
    dataset_title = ""
    for ds in result.datasets:
        resources = mcp.get_dataset_resources(ds.id)
        csv_res = [r for r in resources if getattr(r, "format", "").upper() in ("CSV", "TEXT/CSV")]
        if not csv_res:
            continue
        res = csv_res[0]
        res_id = getattr(res, "id", None) or getattr(res, "resource_id", None)
        try:
            preview = mcp.preview_resource(res_id, page_size=50)
            if preview.columns and preview.rows:
                csv_df = pd.DataFrame(preview.rows, columns=preview.columns)
                dataset_title = ds.title
                break
        except Exception:
            pass
        # MCP preview failed — fall back to direct URL download
        url = getattr(res, "url", None)
        if url:
            try:
                import requests as _req, io as _io, csv as _csv
                raw = _req.get(url, timeout=15).content
                for enc in ("utf-8-sig", "utf-8", "latin-1"):
                    try:
                        text = raw.decode(enc); break
                    except UnicodeDecodeError:
                        continue
                try:
                    sep = _csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
                except _csv.Error:
                    sep = ","
                csv_df = pd.read_csv(_io.StringIO(text), sep=sep, nrows=50)
                dataset_title = ds.title
                break
            except Exception:
                continue

    if csv_df is None:
        pytest.skip("No previewable CSV found via MCP for this query")

    assert not csv_df.empty, "Preview DataFrame is empty"
    print(f"\n✓ data.gouv MCP: '{dataset_title}' → {csv_df.shape[0]} rows × {csv_df.shape[1]} cols")
    print(f"  Columns: {list(csv_df.columns[:6])}")

    # Create a real session from the MCP data
    svc = make_svc(tmp_path)
    state = svc.create_from_tables({f"{dataset_title}.csv": csv_df})
    assert state["current_level"] == 4
    assert state["session_id"]
    print(f"  Session: {state['session_id']} at L{state['current_level']}")


# ──────────────────────────────────────────────────────────────────────────────
# World Bank REST API
# ──────────────────────────────────────────────────────────────────────────────

def test_worldbank_search_indicators(tmp_path):
    """World Bank indicator search returns results."""
    from intuitiveness.services.worldbank_service import WorldBankService

    svc = WorldBankService()
    results = svc.search_indicators("GDP per capita")
    assert len(results) > 0, "No WB indicators found for 'GDP per capita'"
    assert any("GDP" in r.name for r in results), "Results should mention GDP"
    ids = [r.id for r in results]
    print(f"\n✓ World Bank search: {ids[:4]}")


def test_worldbank_fetch_and_import(tmp_path):
    """Fetch GDP per capita + life expectancy, join, create L4 session."""
    from intuitiveness.services.worldbank_service import WorldBankService

    wb = WorldBankService()

    gdp = wb.fetch_indicator("WB_WDI_NY_GDP_PCAP_CD", database_id="WB_WDI")
    life = wb.fetch_indicator("WB_WDI_SP_DYN_LE00_IN", database_id="WB_WDI")

    assert not gdp.empty, "GDP per capita returned empty"
    assert not life.empty, "Life expectancy returned empty"

    print(f"\n✓ World Bank GDP: {gdp.shape[0]} rows — {list(gdp.columns)}")
    print(f"  World Bank Life expectancy: {life.shape[0]} rows — {list(life.columns)}")
    print(f"  Sample: {gdp.head(3).to_dict('records')}")

    # Create session with both tables (multi-source L4)
    svc = make_svc(tmp_path)
    state = svc.create_from_tables({
        "gdp_per_capita.csv": gdp,
        "life_expectancy.csv": life,
    })
    assert state["current_level"] == 4
    assert state["summary"]["source_count"] == 2
    print(f"  Session: {state['session_id']} at L{state['current_level']} "
          f"({state['summary']['source_count']} sources)")
