"""Tests for frontend serving routes."""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


class TestFrontendRoutes:
    """Verify the frontend is served correctly."""

    def test_app_route_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_app_subroute_returns_html(self):
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_static_css_served(self):
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_static_js_api_served(self):
        response = client.get("/static/js/api.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_static_js_app_served(self):
        response = client.get("/static/js/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_api_root_still_works(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI Call Automator"
        assert data["status"] == "running"

    def test_health_still_works(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_api_docs_still_accessible(self):
        response = client.get("/docs")
        assert response.status_code == 200
