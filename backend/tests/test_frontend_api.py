from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_frontend_bootstrap_exposes_ui_contract():
    response = client.get("/api/frontend/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["api_prefix"] == "/api"
    assert payload["defaults"]["simulation_config"]["max_ticks"] >= 1
    assert payload["labels"]["emotions"]
    assert payload["labels"]["graph_layers"]
    assert payload["scenario_bank"]["scenarios"]
    assert "run_big_bang_until_complete" in payload["job_types"]


def test_openapi_includes_frontend_routes():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/frontend/bootstrap" in paths
    assert "/api/frontend/workspace/{big_bang_id}" in paths
    assert "/api/frontend/inspect/{object_type}/{object_id}" in paths


def test_spa_routes_do_not_404_when_frontend_dist_is_missing():
    for path in [
        "/",
        "/big-bangs",
        "/big-bangs/new",
        f"/workspace/00000000-0000-0000-0000-000000000000",
        "/reports",
        "/reports/report/00000000-0000-0000-0000-000000000000",
        "/reports/version/00000000-0000-0000-0000-000000000000",
        "/jobs",
        "/settings",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path


def test_static_mount_does_not_expose_frontend_source_tree():
    response = client.get("/static/package.json")

    assert response.status_code == 404


def test_frontend_inspector_rejects_unknown_type_without_db_query():
    response = client.get("/api/frontend/inspect/unknown/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "unsupported inspector type: unknown"
