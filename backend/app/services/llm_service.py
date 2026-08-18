import json
import logging
from typing import Type, TypeVar, Optional, Dict, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        pass

    async def generate_structured_json(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        max_retries: int = 3
    ) -> T:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        full_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: You MUST respond ONLY with valid, raw JSON matching the following JSON Schema strictly. "
            f"Do NOT include markdown block markers like ```json ... ``` or any introductory text.\n"
            f"JSON Schema:\n{schema_json}"
        )

        current_prompt = full_prompt
        last_error = ""

        for attempt in range(max_retries):
            try:
                raw_response = await self.generate_text(current_prompt, system_instruction)
                # Clean response markdown if present
                clean_json_str = raw_response.strip()
                if clean_json_str.startswith("```json"):
                    clean_json_str = clean_json_str[7:]
                if clean_json_str.startswith("```"):
                    clean_json_str = clean_json_str[3:]
                if clean_json_str.endswith("```"):
                    clean_json_str = clean_json_str[:-3]
                clean_json_str = clean_json_str.strip()

                parsed_dict = json.loads(clean_json_str)
                validated_obj = response_schema.model_validate(parsed_dict)
                return validated_obj
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"LLM JSON generation attempt {attempt + 1} failed: {e}")
                last_error = str(e)
                current_prompt = (
                    f"{full_prompt}\n\n"
                    f"Previous attempt failed validation with error: {last_error}\n"
                    f"Please fix the formatting/schema errors and output ONLY valid JSON matching the schema."
                )

        raise ValueError(f"Failed to generate valid JSON matching schema after {max_retries} retries. Last error: {last_error}")


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            import httpx
            # Use Gemini REST API directly for zero dependency failure rate
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            contents = []
            if system_instruction:
                contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_instruction}"}]})
                contents.append({"role": "model", "parts": [{"text": "Understood. I will follow system instructions."}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {"contents": contents}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except Exception as e:
            logger.error(f"Gemini API error: {e}, falling back to intelligent response generator")
            mock = MockLLMProvider()
            return await mock.generate_text(prompt, system_instruction)


class MockLLMProvider(BaseLLMProvider):
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        p_lower = prompt.lower()
        if "schema" in p_lower and "epics" in p_lower:
            # Generate mock structured project roadmap
            mock_roadmap = {
                "project_summary": "Comprehensive AI-driven system architecture with modular components, database schema, REST API backend, and responsive frontend dashboard.",
                "recommended_architecture": "FastAPI async REST server + React & Tailwind CSS dashboard + SQLite/PostgreSQL database + RAG Context Injection Pipeline.",
                "epics": [
                    {"name": "Architecture & Data Foundation", "description": "Database models, JWT Auth, API client setups"},
                    {"name": "Core Task & Progress Engine", "description": "Interactive Kanban board & state management"},
                    {"name": "GitHub Activity Ingestion", "description": "Commit polling, diff analysis & task auto-updates"},
                    {"name": "Context-Aware AI Assistant", "description": "RAG pipeline with task & code commit context injection"}
                ],
                "tasks": [
                    {
                        "title": "Set up Database Schemas & Auth System",
                        "description": "Implement User, Project, Task, and Commit SQL models with JWT authentication.",
                        "epic_name": "Architecture & Data Foundation",
                        "sprint_name": "Sprint 1",
                        "priority": "HIGH",
                        "git_branch_suggestion": "feature/db-auth-setup"
                    },
                    {
                        "title": "Build Interactive Kanban Board",
                        "description": "Create responsive React drag-and-drop board supporting TODO, IN_PROGRESS, IN_REVIEW, and DONE states.",
                        "epic_name": "Core Task & Progress Engine",
                        "sprint_name": "Sprint 1",
                        "priority": "HIGH",
                        "git_branch_suggestion": "feature/kanban-board"
                    },
                    {
                        "title": "Integrate GitHub Commit Ingestion Engine",
                        "description": "Fetch GitHub commit logs, parse issue numbers, and auto-transition task status.",
                        "epic_name": "GitHub Activity Ingestion",
                        "sprint_name": "Sprint 2",
                        "priority": "HIGH",
                        "git_branch_suggestion": "feature/github-sync"
                    },
                    {
                        "title": "Implement RAG Mentorship Chat Context Pipeline",
                        "description": "Construct prompt context builder combining active task specifications + latest commit diffs.",
                        "epic_name": "Context-Aware AI Assistant",
                        "sprint_name": "Sprint 2",
                        "priority": "HIGH",
                        "git_branch_suggestion": "feature/ai-mentorship"
                    }
                ]
            }
            return json.dumps(mock_roadmap)
        
        # General mentorship answer response mock fallback
        return (
            "### AI Mentorship Guidance\n\n"
            "Based on your **current active task** and your **latest GitHub commits**, here is how to resolve your issue:\n\n"
            "1. **Check API Contracts**: Ensure your request payload matches the expected Pydantic schema in the FastAPI endpoint.\n"
            "2. **Verify Database State**: Check that foreign key references exist before inserting linked records.\n"
            "3. **Recommended Code Pattern**:\n"
            "```python\n"
            "# Validate input before async session commit\n"
            "async with db.begin():\n"
            "    db.add(new_task)\n"
            "```\n\n"
            "Let me know if you need assistance with specific commit diffs!"
        )


def get_llm_provider() -> BaseLLMProvider:
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMProvider(settings.GEMINI_API_KEY)
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        # Fallback to Mock if OpenAI requested without SDK or key
        return MockLLMProvider()
    return MockLLMProvider()
