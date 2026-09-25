from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_and_ready():
    assert client.get("/health").json() == {"status": "ok"}
    r = client.get("/ready")
    assert r.status_code == 200 and "database" in r.json()


def test_freshness_is_cached_and_public():
    r = client.get("/v1/meta/freshness")
    assert r.status_code == 200
    assert r.json()["team"] == "WAS"
    assert r.headers["cache-control"].startswith("public, max-age=")


def test_only_get_is_allowed():
    assert client.post("/health").status_code == 405
