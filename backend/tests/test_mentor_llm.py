import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from app.services.llm_service import GeminiLLMProvider, MockLLMProvider
from app.schemas.planner import RoadmapGenerationOutput

@pytest.mark.asyncio
async def test_gemini_provider_url_and_plain_text():
    provider = GeminiLLMProvider(api_key="test-api-key")
    assert provider.model == "gemini-3.6-flash"

    # Test plain text generation payload & parsing
    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Hello, student! Here is your plain text mentorship advice."}
                    ]
                },
                "finishReason": "STOP"
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: fake_gemini_response

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        result = await provider.generate_text("How do I structure my project?")
        assert result == "Hello, student! Here is your plain text mentorship advice."
        
        # Verify URL called uses gemini-3.6-flash
        call_args = mock_post.call_args
        called_url = call_args[0][0]
        called_json = call_args[1]["json"]
        
        assert "models/gemini-3.6-flash:generateContent" in called_url
        assert "key=test-api-key" in called_url
        # For plain text, responseMimeType should not be set to application/json
        assert "responseMimeType" not in called_json.get("generationConfig", {})

@pytest.mark.asyncio
async def test_gemini_provider_structured_json():
    provider = GeminiLLMProvider(api_key="test-api-key")
    
    fake_json_output = {
        "identified_requirements": ["Requirement 1"],
        "suggested_tech_stack": ["FastAPI", "React"],
        "project_summary": "Test project summary",
        "recommended_architecture": "Test architecture",
        "epics": [{"name": "Core", "description": "Core features"}],
        "tasks": [{
            "title": "Task 1",
            "description": "Desc 1",
            "epic_name": "Core",
            "sprint_name": "Sprint 1",
            "priority": "HIGH",
            "git_branch_suggestion": "feature/task-1"
        }]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": str(fake_json_output).replace("'", '"')}
                    ]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        result = await provider.generate_structured_json(
            prompt="Generate roadmap",
            response_schema=RoadmapGenerationOutput
        )
        assert len(result.epics) == 1
        assert result.epics[0].name == "Core"
        
        # Verify responseMimeType was passed as application/json
        call_args = mock_post.call_args
        called_json = call_args[1]["json"]
        assert called_json["generationConfig"]["responseMimeType"] == "application/json"

@pytest.mark.asyncio
async def test_mentor_chat_endpoints_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        # 1. Register & Login
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Mentor Chat Test Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a test project
        proj_resp = await ac.post("/api/projects", json={
            "title": "AI Mentor Test Project",
            "description": "Testing AI mentor endpoint and plain text responses"
        }, headers=headers)
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        with patch.object(
            GeminiLLMProvider, 
            "generate_text", 
            return_value="### Mentorship Advice\nUse SQLAlchemy relationships with `cascade='all, delete-orphan'`."
        ):
            # 3. Test /api/mentorship/chat
            chat_payload = {
                "project_id": project_id,
                "question": "How should I structure my database relationships?"
            }
            res_mentorship = await ac.post("/api/mentorship/chat", json=chat_payload, headers=headers)
            assert res_mentorship.status_code == 200
            data = res_mentorship.json()
            assert data["sender"] == "AI"
            assert "Mentorship Advice" in data["message"]

            # 4. Test /api/mentor/chat
            res_mentor = await ac.post("/api/mentor/chat", json=chat_payload, headers=headers)
            assert res_mentor.status_code == 200
            assert res_mentor.json()["sender"] == "AI"

            # 5. Test /api/chat
            res_chat = await ac.post("/api/chat", json=chat_payload, headers=headers)
            assert res_chat.status_code == 200
            assert res_chat.json()["sender"] == "AI"

            # 6. Fetch history
            hist_resp = await ac.get(f"/api/mentorship/history/{project_id}", headers=headers)
            assert hist_resp.status_code == 200
            messages = hist_resp.json()
            assert len(messages) >= 6 # 3 user + 3 AI responses


@pytest.mark.asyncio
async def test_mentor_chat_fallback_on_llm_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        # 1. Register & Login
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Fallback Test Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create project
        proj_resp = await ac.post("/api/projects", json={
            "title": "Fallback Test Project",
            "description": "Testing LLM exception handling"
        }, headers=headers)
        project_id = proj_resp.json()["id"]

        # 3. Simulate Gemini LLM error
        with patch.object(
            GeminiLLMProvider, 
            "generate_text", 
            side_effect=Exception("API connection timeout")
        ):
            chat_payload = {
                "project_id": project_id,
                "question": "What should I do if the API fails?"
            }
            res = await ac.post("/api/mentorship/chat", json=chat_payload, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["sender"] == "AI"
            assert "AI Mentorship Guidance" in data["message"]
            assert "API connection timeout" in data["message"]


@pytest.mark.asyncio
async def test_mentor_chat_without_github_connected_smooth_fallback():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        # 1. Register & Login
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "No Git Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create project with NO github repo connected
        proj_resp = await ac.post("/api/projects", json={
            "title": "Standalone Python Microservice",
            "description": "Building a rate limiter using Redis"
        }, headers=headers)
        project_id = proj_resp.json()["id"]

        # 3. Create a specific task
        task_resp = await ac.post("/api/tasks", json={
            "project_id": project_id,
            "title": "Implement Token Bucket Algorithm",
            "description": "Write sliding window rate limiter in Python using Redis pipeline",
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "epic_name": "Rate Limiting",
            "sprint_name": "Sprint 1",
            "git_branch": "feature/token-bucket"
        }, headers=headers)
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]

        # 4. Query mentor chat with active task id and no git repo
        called_prompts = []
        async def fake_generate_text(prompt, system_instruction=None, response_mime_type=None):
            called_prompts.append(prompt)
            return "### Advice for Token Bucket\nImplement Redis `zremrangebyscore` and `zadd`."

        with patch.object(GeminiLLMProvider, "generate_text", side_effect=fake_generate_text):
            chat_payload = {
                "project_id": project_id,
                "active_task_id": task_id,
                "question": "How do I avoid race conditions in Redis?"
            }
            res = await ac.post("/api/mentorship/chat", json=chat_payload, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["sender"] == "AI"
            assert "Token Bucket" in data["message"]
            
            # Verify prompt contains task details and fallback for GitHub
            assert len(called_prompts) == 1
            sent_prompt = called_prompts[0]
            assert "Implement Token Bucket Algorithm" in sent_prompt
            assert "Write sliding window rate limiter" in sent_prompt
            assert "No GitHub repository connected" in sent_prompt

