"""Smoke test validating mock Conduit endpoints and response schema."""

import httpx
import pytest

from locust_perf_kit.mock_server.server import MockConduitServer


@pytest.fixture(scope="module")
def mock_server():
    server = MockConduitServer(port=8089)
    server.start()
    yield server
    server.stop()


def test_smoke_health(mock_server):
    res = httpx.get("http://127.0.0.1:8089/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_smoke_tags(mock_server):
    res = httpx.get("http://127.0.0.1:8089/api/tags")
    assert res.status_code == 200
    data = res.json()
    assert "tags" in data
    assert "performance" in data["tags"]


def test_smoke_articles_feed(mock_server):
    res = httpx.get("http://127.0.0.1:8089/api/articles?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["articlesCount"] >= 1
    assert data["articles"][0]["slug"] == "perf-test-slug-1"


def test_smoke_author_login_and_create(mock_server):
    login_res = httpx.post(
        "http://127.0.0.1:8089/api/users/login",
        json={"user": {"email": "tester@example.com", "password": "password123"}},
    )
    assert login_res.status_code == 200
    token = login_res.json()["user"]["token"]
    assert token == "mock-jwt-token-xyz-123"

    article_res = httpx.post(
        "http://127.0.0.1:8089/api/articles",
        headers={"Authorization": f"Token {token}"},
        json={
            "article": {
                "title": "Smoke Article",
                "description": "Short description",
                "body": "Article content",
            }
        },
    )
    assert article_res.status_code == 201
    assert article_res.json()["article"]["slug"] == "smoke-article"
