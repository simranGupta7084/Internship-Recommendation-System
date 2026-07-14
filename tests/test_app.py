import numpy as np
import pytest
import database
import matcher
import app as app_module


@pytest.fixture
def client(monkeypatch):
    # Same fake-embedding trick as test_matcher: keep these tests fast and offline.
    def fake_embed(texts):
        return np.array([[1.0, 0.0]] + [[0.9, 0.1]] * (len(texts) - 1))
    monkeypatch.setattr(matcher, "embed", fake_embed)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    database.internships_col.delete_many({})
    database.profiles_col.delete_many({})


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_admin_refresh_requires_api_key(client):
    resp = client.post("/admin/refresh", json={})
    assert resp.status_code == 401


def test_admin_refresh_rejects_wrong_key(client):
    resp = client.post("/admin/refresh", json={}, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_profile_requires_name(client):
    resp = client.post("/profile", json={"skills": ["python"]}, headers={"X-API-Key": "test-key"})
    assert resp.status_code == 400


def test_profile_create_and_fetch(client):
    resp = client.post(
        "/profile",
        json={"name": "bob", "skills": ["python", "sql"], "resume_text": "I know Python and SQL"},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 200

    fetched = client.get("/profile/bob")
    assert fetched.status_code == 200
    assert fetched.get_json()["skills"] == ["python", "sql"]


def test_recommend_without_cached_internships_returns_409(client):
    resp = client.post("/recommend", json={"resume": "python developer"})
    assert resp.status_code == 409


def test_recommend_end_to_end(client):
    database.insert_internship({
        "title": "Python Intern", "company": "Acme", "location": "Remote",
        "description": "Work with Flask and SQL",
    })
    resp = client.post("/recommend", json={"resume": "I know Python, Flask, SQL"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["results"]) == 1
    assert body["results"][0]["title"] == "Python Intern"


def test_internships_pagination_metadata(client):
    for i in range(3):
        database.insert_internship({
            "title": f"Intern {i}", "company": "Acme", "location": "Remote", "description": "x",
        })
    resp = client.get("/internships?per_page=2&page=1")
    body = resp.get_json()
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
