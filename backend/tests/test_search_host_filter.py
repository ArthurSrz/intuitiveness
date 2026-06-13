"""Regression: /search must not list datasets the import endpoint will reject.

Import only accepts CSV resources hosted on data.gouv.fr (external hosts are
unreliable — see _resolve_csv_candidates). Search must therefore apply the
SAME host filter, or users see datasets that always fail with
"No data.gouv.fr-hosted CSV found".
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
                "title": "CSV only on an external host",
                "description": "phantom",
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


def test_search_excludes_datasets_without_hosted_csv(client):
    with patch("app.routers.search.requests.get", return_value=_FakeResp(_fake_datagouv_payload())):
        resp = client.get("/search", params={"q": "sante"})
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()["datasets"]]
    assert "ds-hosted" in ids
    assert "ds-no-csv" not in ids
    # The phantom: import would 404 on it, so search must not show it.
    assert "ds-external" not in ids


def test_import_rejects_external_only_dataset(client):
    """The import-side behavior the search filter must mirror."""
    dataset_payload = {
        "id": "ds-external",
        "resources": [
            {"format": "CSV", "url": "https://data-atmoaura.opendata.arcgis.com/x.csv", "title": "x"},
        ],
    }
    with patch("app.routers.search.requests.get", return_value=_FakeResp(dataset_payload)):
        resp = client.post(
            "/sessions/import-url",
            json={"url": "https://www.data.gouv.fr/fr/datasets/ds-external/"},
        )
    assert resp.status_code == 404
    assert "No data.gouv.fr-hosted CSV" in resp.json()["detail"]
