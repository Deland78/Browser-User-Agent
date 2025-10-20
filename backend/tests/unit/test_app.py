"""Unit tests for FastAPI application factory and middleware."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from browser_agent.app import create_app
from browser_agent.config import settings


class TestFastAPIApp:
    """Test suite for FastAPI application configuration and endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI app."""
        app = create_app()
        return TestClient(app)

    def test_health_endpoint_returns_200(self, client):
        """Test that health endpoint returns 200 OK status."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_response_structure(self, client):
        """Test that health endpoint returns expected JSON structure."""
        response = client.get("/api/v1/health")

        # Verify response is JSON
        assert response.headers["content-type"] == "application/json"

        # Verify response structure
        data = response.json()
        assert "status" in data
        assert "environment" in data
        assert "version" in data

        # Verify values
        assert data["status"] == "ok"
        assert data["environment"] == settings.environment
        assert data["version"] == "0.1.0"

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present for allowed origins."""
        # Make a preflight OPTIONS request
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )

        # Verify CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "access-control-allow-methods" in response.headers

    def test_cors_allows_configured_origins(self, client):
        """Test that CORS allows origins from settings."""
        # Test first configured origin
        origin = settings.cors_origins[0]
        response = client.get(
            "/api/v1/health",
            headers={"Origin": origin}
        )

        assert response.headers.get("access-control-allow-origin") == origin

    def test_validation_error_handler(self, client):
        """Test that validation errors return 422 with proper structure."""
        # This will be useful when we have endpoints with request bodies
        # For now, we'll test by making an invalid request to a future endpoint

        # Since we only have /health endpoint, we'll test the handler exists
        # by checking that the app has the exception handler registered
        app = create_app()
        from fastapi.exceptions import RequestValidationError

        # Verify the exception handler is registered
        assert RequestValidationError in app.exception_handlers

        # The handler should return a JSONResponse with:
        # - status_code: 422
        # - content: {"error": "Validation Error", "message": "...", "details": [...]}

    def test_generic_exception_handler(self, client):
        """Test that unexpected exceptions return 500 with proper structure."""
        # We can't easily trigger a generic exception with just /health endpoint
        # but we can verify the handler is registered
        app = create_app()

        # Verify the exception handler is registered for Exception
        assert Exception in app.exception_handlers

        # The handler should return a JSONResponse with:
        # - status_code: 500
        # - content: {"error": "Internal Server Error", "message": "..."}

    def test_health_endpoint_method_not_allowed(self, client):
        """Test that health endpoint only accepts GET requests."""
        # Try POST (should fail)
        response = client.post("/api/v1/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_api_v1_prefix(self, client):
        """Test that health endpoint is accessible at /api/v1 prefix."""
        # Verify it's at /api/v1/health
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

        # Verify it's NOT at /health (without prefix)
        response = client.get("/health")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_openapi_docs_available(self, client):
        """Test that OpenAPI documentation is accessible."""
        response = client.get("/docs")

        # Should return HTML (Swagger UI)
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema JSON is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"

        # Verify schema structure
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Browser Automation Agent"
        assert schema["info"]["version"] == "0.1.0"

    def test_cors_credentials_allowed(self, client):
        """Test that CORS allows credentials."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"}
        )

        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_cors_all_methods_allowed(self, client):
        """Test that CORS allows all HTTP methods."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            }
        )

        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "PUT" in allowed_methods
        assert "DELETE" in allowed_methods
        assert "OPTIONS" in allowed_methods

    def test_app_title_and_description(self, client):
        """Test that app has correct title and description."""
        app = create_app()

        assert app.title == "Browser Automation Agent"
        assert app.version == "0.1.0"
        assert "browser automation" in app.description.lower()
