import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.config import settings
from app.services.llm_service import GeminiLLMProvider, MockLLMProvider, GeminiQuotaExceededError
from app.schemas.planner import RoadmapGenerationOutput
from app.services.mentorship_service import _MENTORSHIP_QUERY_CACHE

@pytest.mark.asyncio
async def test_gemini_provider_url_and_plain_text():
    provider = GeminiLLMProvider(api_key="test-api-key")
    assert provider.model == settings.GEMINI_MODEL

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
        
        # Verify URL called uses configured model
        call_args = mock_post.call_args
        called_url = call_args[0][0]
        called_json = call_args[1]["json"]
        
        assert f"models/{settings.GEMINI_MODEL}:generateContent" in called_url
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


@pytest.mark.asyncio
async def test_gemini_retry_on_network_errors_and_backoff():
    provider = GeminiLLMProvider(api_key="test-api-key")

    mock_resp_success = AsyncMock()
    mock_resp_success.status_code = 200
    mock_resp_success.json = lambda: {
        "candidates": [{
            "content": {"parts": [{"text": "Success after transient network glitches!"}]},
            "finishReason": "STOP"
        }]
    }

    # Simulate: 1st call fails with ReadTimeout, 2nd fails with ConnectError, 3rd succeeds
    call_count = 0
    async def side_effect_post(url, json=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise import_httpx.ReadTimeout("Read timeout from upstream")
        elif call_count == 2:
            raise import_httpx.ConnectError("[Errno 11001] getaddrinfo failed")
        return mock_resp_success

    import httpx as import_httpx
    with patch("asyncio.sleep", return_value=None), patch("httpx.AsyncClient.post", side_effect=side_effect_post):
        result = await provider.generate_text("Test prompt")
        assert result == "Success after transient network glitches!"
        assert call_count == 3


@pytest.mark.asyncio
async def test_gemini_retry_exhaustion_logs_clear_error():
    provider = GeminiLLMProvider(api_key="test-api-key")

    mock_resp_503 = AsyncMock()
    mock_resp_503.status_code = 503
    mock_resp_503.reason_phrase = "Service Unavailable"
    mock_resp_503.text = "This model is currently experiencing high demand"

    with patch("asyncio.sleep", return_value=None), patch("httpx.AsyncClient.post", return_value=mock_resp_503):
        with pytest.raises(ValueError) as exc_info:
            await provider.generate_text("Overloaded model prompt")
        assert "503" in str(exc_info.value)
        assert "5 attempts" in str(exc_info.value)


@pytest.mark.asyncio
async def test_planner_generate_graceful_fallback_on_llm_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Planner Fallback Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Simulate Gemini throwing ReadTimeout / 503
        with patch.object(
            GeminiLLMProvider,
            "generate_structured_json",
            side_effect=ValueError("Gemini API connection/timeout error (ReadTimeout) after 5 attempts")
        ):
            planner_payload = {
                "idea_title": "AI Plant Disease Classifier",
                "idea_description": "Mobile app allowing farmers to take photos of crops to detect diseases using CNN models.",
                "tech_stack": ["React Native", "PyTorch"],
                "duration_weeks": 8,
                "team_size": 3
            }
            res = await ac.post("/api/planner/generate", json=planner_payload, headers=headers)
            # Must return 200 OK with graceful fallback starter roadmap
            assert res.status_code == 200
            data = res.json()
            assert "identified_requirements" in data
            assert len(data["identified_requirements"]) > 0
            assert "suggested_tech_stack" in data
            assert "PyTorch" in data["suggested_tech_stack"]
            assert len(data["epics"]) >= 3
            assert len(data["tasks"]) >= 3
            assert "Note: Gemini AI is currently experiencing high network demand" in data["stack_rationale"]


@pytest.mark.asyncio
async def test_gemini_quota_exhausted_fails_fast_without_retries():
    provider = GeminiLLMProvider(api_key="test-api-key")

    mock_resp_429 = AsyncMock()
    mock_resp_429.status_code = 429
    mock_resp_429.reason_phrase = "Too Many Requests"
    mock_resp_429.text = '{"error": {"code": 429, "message": "RESOURCE_EXHAUSTED: quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"}}'

    call_count = 0
    async def side_effect_post(url, json=None):
        nonlocal call_count
        call_count += 1
        return mock_resp_429

    with patch("httpx.AsyncClient.post", side_effect=side_effect_post):
        with pytest.raises(GeminiQuotaExceededError) as exc_info:
            await provider.generate_text("Student prompt")
        assert "RESOURCE_EXHAUSTED" in str(exc_info.value)
        # Verify it failed fast on attempt 1 without sleeping / wasting retries
        assert call_count == 1


@pytest.mark.asyncio
async def test_mentorship_chat_cache_prevents_duplicate_llm_calls():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Cache Test Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        proj_resp = await ac.post("/api/projects", json={
            "title": "Caching Test Project",
            "description": "Testing in-memory cache"
        }, headers=headers)
        project_id = proj_resp.json()["id"]

        call_count = 0
        async def mock_generate(prompt, system_instruction=None, response_mime_type=None, timeout=90.0):
            nonlocal call_count
            call_count += 1
            return f"### AI Response #{call_count}\nAlways validate input schemas with Pydantic."

        with patch.object(GeminiLLMProvider, "generate_text", side_effect=mock_generate):
            chat_payload = {
                "project_id": project_id,
                "question": "How do I validate API inputs with Pydantic?"
            }
            # 1. First call: Cache miss, calls LLM
            res1 = await ac.post("/api/mentorship/chat", json=chat_payload, headers=headers)
            assert res1.status_code == 200
            assert "AI Response #1" in res1.json()["message"]
            assert call_count == 1

            # 2. Second call with identical/similar normalized question: Cache hit, skips LLM
            res2 = await ac.post("/api/mentorship/chat", json={
                "project_id": project_id,
                "question": "  how  do i validate api inputs with pydantic?  "
            }, headers=headers)
            assert res2.status_code == 200
            assert "AI Response #1" in res2.json()["message"]
            # Call count should STILL be 1 (LLM was NOT called again!)
            assert call_count == 1


@pytest.mark.asyncio
async def test_mentorship_chat_quota_exhaustion_friendly_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Quota Notice Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        proj_resp = await ac.post("/api/projects", json={
            "title": "Quota Notice Project",
            "description": "Testing quota notice"
        }, headers=headers)
        project_id = proj_resp.json()["id"]

        with patch.object(
            GeminiLLMProvider,
            "generate_text",
            side_effect=GeminiQuotaExceededError("RESOURCE_EXHAUSTED: daily limit reached")
        ):
            chat_payload = {
                "project_id": project_id,
                "question": "What is the best way to write unit tests for FastAPI?"
            }
            res = await ac.post("/api/mentorship/chat", json=chat_payload, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["sender"] == "AI"
            assert "AI Academic Mentor Notice" in data["message"]
            assert "free-tier allocation" in data["message"]


@pytest.mark.asyncio
async def test_planner_generate_quota_exhaustion_notice():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_email = f"student_{uuid.uuid4().hex[:6]}@univ.edu"
        
        reg_resp = await ac.post("/api/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Planner Quota Student",
            "role": "STUDENT"
        })
        assert reg_resp.status_code == 201

        login_resp = await ac.post("/api/auth/login", data={
            "username": test_email,
            "password": "password123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(
            GeminiLLMProvider,
            "generate_structured_json",
            side_effect=GeminiQuotaExceededError("RESOURCE_EXHAUSTED")
        ):
            planner_payload = {
                "idea_title": "AI Video Captioning Tool",
                "idea_description": "Speech to text transcript generator using Whisper models.",
                "duration_weeks": 6,
                "team_size": 2
            }
            res = await ac.post("/api/planner/generate", json=planner_payload, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert "daily free-tier quota has been reached on this model" in data["stack_rationale"]



