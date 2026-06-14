"""Search and import: CSV-format filtering.

Search only shows datasets that have at least one CSV resource.
Import accepts any CSV URL returned by the data.gouv.fr API (the platform
already vets uploads, so no host allowlist is needed).
"""

from __future__ import annotations

from unittest.mock import patch


def _fake_datagouv_payload():
    return {
        "data": [
            {
                "id": "ds-hosted",
                "title": "Hosted on data.gouv.fr",
                "description": "ok",
                "organization": {"name": "Org A"},
                "resources": [
                    {"format": "csv", "url": "https://www.data.gouv.fr/fr/datasets/r/abc.csv", "title": "abc"},
                ],
            },
            {
                "id": "ds-external",
                "title": "CSV on an external host",
                "description": "external but valid",
                "organization": {"name": "Org B"},
                "resources": [
                    {"format": "csv", "url": "https://data-atmoaura.opendata.arcgis.com/x.csv", "title": "x"},
                ],
            },
            {
                "id": "ds-no-csv",
                "title": "No CSV at all",
                "description": "json only",
                "organization": {"name": "Org C"},
                "resources": [
                    {"format": "json", "url": "https://www.data.gouv.fr/fr/datasets/r/y.json", "title": "y"},
                ],
            },
        ],
        "total": 3,
        "next_page": None,
    }


class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_search_shows_all_csv_datasets(client):
    """Both .gouv.fr-hosted and external CSVs should appear in results."""
    with patch("app.routers.search._search_via_mcp", return_value=None), \
         patch("app.routers.search.requests.get", return_value=_FakeResp(_fake_datagouv_payload())):
        resp = client.get("/search", params={"q": "sante"})
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()["datasets"]]
    assert "ds-hosted" in ids
    assert "ds-external" in ids
    assert "ds-no-csv" not in ids


def test_search_excludes_non_csv_datasets(client):
    with patch("app.routers.search._search_via_mcp", return_value=None), \
         patch("app.routers.search.requests.get", return_value=_FakeResp(_fake_datagouv_payload())):
        resp = client.get("/search", params={"q": "sante"})
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()["datasets"]]
    assert "ds-no-csv" not in ids
