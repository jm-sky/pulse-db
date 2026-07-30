"""Unit tests for ConvertEmptyStringsToNoneMiddleware."""

import json

import pytest
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.convert_empty_strings_middleware import (
    ConvertEmptyStringsToNoneMiddleware,
    _convert_empty_strings_to_none,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI app with the middleware."""
    app = FastAPI()

    @app.post("/test")
    async def test_endpoint(request: Request) -> JSONResponse:
        """Test endpoint that returns the request body."""
        body = await request.body()
        data = json.loads(body) if body else {}
        return JSONResponse(content={"received": data})

    @app.put("/test")
    async def test_put_endpoint(request: Request) -> JSONResponse:
        """Test PUT endpoint."""
        body = await request.body()
        data = json.loads(body) if body else {}
        return JSONResponse(content={"received": data})

    @app.patch("/test")
    async def test_patch_endpoint(request: Request) -> JSONResponse:
        """Test PATCH endpoint."""
        body = await request.body()
        data = json.loads(body) if body else {}
        return JSONResponse(content={"received": data})

    @app.get("/test")
    async def test_get_endpoint() -> JSONResponse:
        """Test GET endpoint (should not be processed by middleware)."""
        return JSONResponse(content={"message": "GET request"})

    # Add middleware
    app.add_middleware(ConvertEmptyStringsToNoneMiddleware)

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


class TestConvertEmptyStringsToNoneMiddleware:
    """Tests for ConvertEmptyStringsToNoneMiddleware."""

    def test_converts_empty_strings_to_none_in_simple_object(self, client: TestClient) -> None:
        """Test that empty strings are converted to None in simple objects."""
        data = {
            "name": "John",
            "email": "",
            "age": 25,
            "description": "",
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["name"] == "John"
        assert result["received"]["email"] is None
        assert result["received"]["age"] == 25
        assert result["received"]["description"] is None

    def test_converts_empty_strings_in_nested_objects(self, client: TestClient) -> None:
        """Test that empty strings are converted in nested objects."""
        data = {
            "user": {
                "name": "John",
                "email": "",
                "profile": {
                    "bio": "",
                    "avatar": "https://example.com/avatar.jpg",
                },
            },
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["user"]["name"] == "John"
        assert result["received"]["user"]["email"] is None
        assert result["received"]["user"]["profile"]["bio"] is None
        assert result["received"]["user"]["profile"]["avatar"] == "https://example.com/avatar.jpg"

    def test_converts_empty_strings_in_arrays(self, client: TestClient) -> None:
        """Test that empty strings are converted in arrays."""
        data = {
            "tags": ["tag1", "", "tag3"],
            "items": [
                {"name": "item1", "description": ""},
                {"name": "", "description": "desc2"},
            ],
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["tags"] == ["tag1", None, "tag3"]
        assert result["received"]["items"][0]["name"] == "item1"
        assert result["received"]["items"][0]["description"] is None
        assert result["received"]["items"][1]["name"] is None
        assert result["received"]["items"][1]["description"] == "desc2"

    def test_preserves_non_empty_strings(self, client: TestClient) -> None:
        """Test that non-empty strings are preserved."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "description": "Some description",
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["name"] == "John Doe"
        assert result["received"]["email"] == "john@example.com"
        assert result["received"]["description"] == "Some description"

    def test_preserves_other_types(self, client: TestClient) -> None:
        """Test that non-string types are preserved."""
        data = {
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null_value": None,
            "array": [1, 2, 3],
            "object": {"key": "value"},
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["number"] == 42
        assert result["received"]["float"] == 3.14
        assert result["received"]["boolean"] is True
        assert result["received"]["null_value"] is None
        assert result["received"]["array"] == [1, 2, 3]
        assert result["received"]["object"] == {"key": "value"}

    def test_works_with_put_method(self, client: TestClient) -> None:
        """Test that middleware works with PUT method."""
        data = {"name": "John", "email": ""}
        response = client.put("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["name"] == "John"
        assert result["received"]["email"] is None

    def test_works_with_patch_method(self, client: TestClient) -> None:
        """Test that middleware works with PATCH method."""
        data = {"name": "John", "email": ""}
        response = client.patch("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["name"] == "John"
        assert result["received"]["email"] is None

    def test_does_not_process_get_method(self, client: TestClient) -> None:
        """Test that GET requests are not processed by middleware."""
        response = client.get("/test")
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["message"] == "GET request"

    def test_handles_invalid_json_gracefully(self, client: TestClient) -> None:
        """Test that invalid JSON is handled gracefully."""
        # This should not crash - middleware should let Pydantic handle validation
        response = client.post(
            "/test",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        # Should return error, but not crash
        assert response.status_code in (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_handles_empty_body(self, client: TestClient) -> None:
        """Test that empty body is handled correctly."""
        response = client.post("/test", json={})
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"] == {}

    def test_handles_non_json_content_type(self, client: TestClient) -> None:
        """Test that non-JSON content types are not processed."""
        # Send as form data (should not be processed)
        response = client.post(
            "/test",
            data={"name": "John", "email": ""},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # Should return error because endpoint expects JSON
        assert response.status_code in (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_complex_nested_structure(self, client: TestClient) -> None:
        """Test with complex nested structure."""
        data = {
            "container": {
                "name": "Backpack",
                "description": "",
                "items": [
                    {"name": "Item 1", "notes": ""},
                    {"name": "", "notes": "Some notes"},
                ],
                "metadata": {
                    "tags": ["tag1", "", "tag3"],
                    "url": "",
                },
            },
        }
        response = client.post("/test", json=data)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["received"]["container"]["name"] == "Backpack"
        assert result["received"]["container"]["description"] is None
        assert result["received"]["container"]["items"][0]["name"] == "Item 1"
        assert result["received"]["container"]["items"][0]["notes"] is None
        assert result["received"]["container"]["items"][1]["name"] is None
        assert result["received"]["container"]["items"][1]["notes"] == "Some notes"
        assert result["received"]["container"]["metadata"]["tags"] == [
            "tag1",
            None,
            "tag3",
        ]
        assert result["received"]["container"]["metadata"]["url"] is None

    def test_convert_empty_strings_to_none_function(self) -> None:
        """Test the _convert_empty_strings_to_none function directly."""
        # Test simple dict
        assert _convert_empty_strings_to_none({"a": "", "b": "value"}) == {
            "a": None,
            "b": "value",
        }

        # Test nested dict
        assert _convert_empty_strings_to_none({"a": {"b": "", "c": "value"}}) == {"a": {"b": None, "c": "value"}}

        # Test list
        assert _convert_empty_strings_to_none(["", "value", ""]) == [
            None,
            "value",
            None,
        ]

        # Test nested list
        assert _convert_empty_strings_to_none([{"a": ""}, {"b": "value"}]) == [
            {"a": None},
            {"b": "value"},
        ]

        # Test non-string values
        assert _convert_empty_strings_to_none({"a": 1, "b": True, "c": None}) == {
            "a": 1,
            "b": True,
            "c": None,
        }

        # Test empty string
        assert _convert_empty_strings_to_none("") is None

        # Test non-empty string
        assert _convert_empty_strings_to_none("value") == "value"

        # Test number
        assert _convert_empty_strings_to_none(42) == 42
