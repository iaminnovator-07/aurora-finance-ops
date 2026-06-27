"""Authentication API integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@aurora.com", "password": "securepass123", "full_name": "Test User"},
    )
    assert register.status_code == 200
    data = register.json()["data"]
    assert data["user"]["email"] == "test@aurora.com"
    assert "access_token" in data["tokens"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@aurora.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["tokens"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/emails")
    assert response.status_code == 401
