from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_layers_are_config_driven():
    response = client.get("/api/layers")
    assert response.status_code == 200
    layers = response.json()["layers"]
    assert {layer["id"] for layer in layers} == {"wetlands", "floodplain", "transmission"}
    assert all("default_setback_m" in layer and "guidance_url" in layer for layer in layers)
    assert response.json()["default_profile"] == "screening"
    assert {profile["id"] for profile in response.json()["profiles"]} == {"screening", "footprint-only"}


def test_parcel_search_and_fetch_contract():
    search = client.get("/api/parcels/search", params={"limit": 10})
    assert search.status_code == 200
    assert search.json()["total"] > 100
    assert len(search.json()["parcels"]) == 10
    parcel_id = search.json()["parcels"][0]["id"]
    assert parcel_id.startswith("TNRIS-48027-")
    assert client.get(f"/api/parcels/{parcel_id}").status_code == 200
    assert client.get("/api/parcels/TRAVIS-DEMO-001").status_code == 200
    assert client.get("/api/parcels/missing").status_code == 404


def test_analyze_by_parcel_id_uses_defaults_and_returns_diagnostics():
    response = client.post("/api/analyze", json={"parcel_id": "TRAVIS-DEMO-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_crs"] == "EPSG:32614"
    assert body["parcel_acres"] > body["buildable_acres"] > 0
    assert len(body["breakdown"]) == 3
    assert "duplicate_overlap_acres" in body["overlap_diagnostics"]
    assert body["policy"]["config_version"] == "2026.06.1"
    assert body["policy"]["profile_id"] == "screening"
    assert len(body["policy"]["assumptions"]) == 3


def test_catalog_search_supports_pagination_and_bbox():
    first = client.get("/api/parcels/search", params={"limit": 5}).json()
    second = client.get("/api/parcels/search", params={"limit": 5, "offset": 5}).json()
    assert first["total"] == second["total"]
    assert {row["id"] for row in first["parcels"]}.isdisjoint(row["id"] for row in second["parcels"])
    spatial = client.get("/api/parcels/search", params={"bbox": "-97.45,31.06,-97.44,31.07"}).json()
    assert 0 < spatial["total"] < first["total"]


def test_analyze_rejects_unknown_layer_and_ambiguous_parcel_input():
    unknown = client.post("/api/analyze", json={
        "parcel_id": "TRAVIS-DEMO-001",
        "layers": [{"id": "not-real"}],
    })
    assert unknown.status_code == 422
    ambiguous = client.post("/api/analyze", json={
        "parcel_id": "TRAVIS-DEMO-001",
        "parcel": {"type": "Polygon", "coordinates": []},
    })
    assert ambiguous.status_code == 422


def test_bbox_validation_returns_clean_422():
    response = client.get("/api/parcels/search", params={"bbox": "1,2,nope,4"})
    assert response.status_code == 422


def test_policy_profiles_and_layer_bounds_are_enforced():
    footprint = client.post("/api/analyze", json={
        "parcel_id": "TRAVIS-DEMO-001",
        "policy_profile": "footprint-only",
    })
    assert footprint.status_code == 200
    assert all(row["setback_m"] == 0 for row in footprint.json()["breakdown"][:3])

    unknown = client.post("/api/analyze", json={
        "parcel_id": "TRAVIS-DEMO-001",
        "policy_profile": "not-a-policy",
    })
    assert unknown.status_code == 422

    excessive = client.post("/api/analyze", json={
        "parcel_id": "TRAVIS-DEMO-001",
        "layers": [{"id": "wetlands", "setback_m": 200}],
    })
    assert excessive.status_code == 422
