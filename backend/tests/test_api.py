import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "online"

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_register_and_login_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"test_{uuid.uuid4().hex[:6]}@univ.edu"
        # Register user
        reg_payload = {
            "email": test_email,
            "password": "password123",
            "full_name": "Test User",
            "role": "STUDENT",
            "github_username": "testuser"
        }
        reg_resp = await ac.post("/api/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201
        assert reg_resp.json()["email"] == test_email

        # Login user
        login_data = {
            "username": test_email,
            "password": "password123"
        }
        login_resp = await ac.post("/api/auth/login", data=login_data)
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        assert "access_token" in tokens
        token = tokens["access_token"]

        # Fetch current user me
        me_resp = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == test_email
