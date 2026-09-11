import asyncio
import json
import logging
from typing import Type, TypeVar, Optional, Dict, Any
from abc import ABC, abstractmethod
import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        timeout: float = 90.0
    ) -> str:
        pass

    async def generate_structured_json(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 120.0
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
                raw_response = await self.generate_text(
                    current_prompt,
                    system_instruction,
                    response_mime_type="application/json",
                    timeout=timeout
                )
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
                logger.warning(f"LLM JSON generation attempt {attempt + 1} validation failed: {e}")
                last_error = str(e)
                current_prompt = (
                    f"{full_prompt}\n\n"
                    f"Previous attempt failed validation with error: {last_error}\n"
                    f"Please fix the formatting/schema errors and output ONLY valid JSON matching the schema."
                )

        raise ValueError(f"Failed to generate valid JSON matching schema after {max_retries} retries. Last error: {last_error}")


class GeminiQuotaExceededError(Exception):
    """Raised when Gemini API responds with 429 RESOURCE_EXHAUSTED / quota limit reached."""
    pass


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.6-flash")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        timeout: float = 90.0
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        gen_config: Dict[str, Any] = {
            "temperature": 0.4
        }
        if response_mime_type:
            gen_config["responseMimeType"] = response_mime_type

        payload: Dict[str, Any] = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": gen_config
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Exponential backoff retry loop (5 attempts: 2s, 4s, 8s, 16s, 30s)
        backoff_delays = [2.0, 4.0, 8.0, 16.0, 30.0]
        max_attempts = len(backoff_delays)
        last_error_details = None

        client_timeout = httpx.Timeout(timeout=timeout, connect=30.0, read=timeout, write=30.0)

        for attempt in range(max_attempts):
            delay = backoff_delays[attempt]
            try:
                async with httpx.AsyncClient(timeout=client_timeout) as client:
                    resp = await client.post(url, json=payload)
                
                # Check specifically for hard Quota Exhaustion (RESOURCE_EXHAUSTED / daily model limit)
                if resp.status_code == 429:
                    resp_text = resp.text
                    is_quota_exhausted = any(
                        marker in resp_text
                        for marker in [
                            "RESOURCE_EXHAUSTED",
                            "quotaId",
                            "GenerateRequestsPerDay",
                            "Quota exceeded",
                            "exceeded your current quota",
                            "rateLimitExceeded"
                        ]
                    )
                    if is_quota_exhausted:
                        logger.warning(
                            f"[GeminiLLMProvider] Gemini API Free-Tier Quota Exhausted (429 RESOURCE_EXHAUSTED): {resp_text}. "
                            f"Failing fast without retry."
                        )
                        raise GeminiQuotaExceededError(
                            f"Gemini API quota exhausted (RESOURCE_EXHAUSTED): {resp_text}"
                        )
                    
                # Check for transient / retryable status codes (transient 429, 503 Service Unavailable, 5xx)
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error_details = f"HTTP {resp.status_code} ({resp.reason_phrase}): {resp.text}"
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"[GeminiLLMProvider] Gemini API returned HTTP {resp.status_code} ({resp.reason_phrase}). "
                            f"Retrying with exponential backoff in {delay}s (Attempt {attempt + 1}/{max_attempts})..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"[GeminiLLMProvider] Gemini API call failed after {max_attempts} attempts. "
                            f"Final HTTP Status: {resp.status_code} ({resp.reason_phrase}). Response: {resp.text}"
                        )
                        raise ValueError(f"Gemini API returned HTTP {resp.status_code} ({resp.reason_phrase}) after {max_attempts} attempts: {resp.text}")
                
                # Non-200 non-retryable error (e.g. 400 Bad Request, 403 Forbidden)
                if resp.status_code != 200:
                    logger.error(
                        f"[GeminiLLMProvider] Gemini API non-retryable error HTTP {resp.status_code} ({resp.reason_phrase}): {resp.text}"
                    )
                    raise ValueError(f"Gemini API Failed with Status {resp.status_code}: {resp.text}")
                    
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    feedback = data.get("promptFeedback", {})
                    block_reason = feedback.get("blockReason", "Unknown")
                    raise ValueError(f"Gemini API returned no candidates (Block reason: {block_reason}). Full response: {data}")
                
                first_candidate = candidates[0]
                content = first_candidate.get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    finish_reason = first_candidate.get("finishReason", "Unknown")
                    raise ValueError(f"Gemini API returned candidate with no parts (finishReason: {finish_reason}). Full response: {data}")
                
                text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                text = "".join(text_parts).strip()
                if not text:
                    raise ValueError(f"Gemini API returned empty text part. Full response: {data}")
                return text

            except (httpx.RequestError, OSError, ConnectionError, TimeoutError) as net_err:
                err_type = type(net_err).__name__
                err_msg = str(net_err) or "(no error message provided)"
                last_error_details = f"{err_type}: {err_msg}"
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"[GeminiLLMProvider] Network/DNS/timeout error ({err_type}: {err_msg}). "
                        f"Retrying in {delay}s (Attempt {attempt + 1}/{max_attempts})..."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"[GeminiLLMProvider] Gemini API network/DNS/timeout failure after {max_attempts} attempts. "
                        f"Final Error Type: {err_type}, Message: {err_msg}"
                    )
                    raise ValueError(f"Gemini API connection/timeout error ({err_type}) after {max_attempts} attempts: {err_msg}")

        raise ValueError(f"Gemini API call failed after {max_attempts} attempts: {last_error_details}")



class MockLLMProvider(BaseLLMProvider):
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        timeout: float = 90.0
    ) -> str:
        p_lower = prompt.lower()
        if "schema" in p_lower or "epics" in p_lower or "roadmap" in p_lower:
            # Isolate user project content before schema section to avoid false positive keyword matching
            project_content = prompt.split("JSON Schema:")[0].split("IMPORTANT:")[0].lower()

            # Check for user-provided tech stack in prompt
            user_stack = None
            if "student preferred tech stack:" in project_content:
                stack_line = [l for l in prompt.split("\n") if "student preferred tech stack:" in l.lower()]
                if stack_line:
                    raw_val = stack_line[0].split(":", 1)[1].strip()
                    if raw_val and "none" not in raw_val.lower() and "not specified" not in raw_val.lower():
                        user_stack = [s.strip() for s in raw_val.split(",") if s.strip()]

            # Computer Vision / Image Intelligence
            if any(k in project_content for k in ["image", "vision", "plant", "disease", "face", "camera", "opencv", "cnn", "yolo", "leaf", "medical", "scan", "photo"]):
                tech_stack = user_stack or ["React (Vite)", "FastAPI / Flask", "PyTorch / torchvision", "OpenCV / Pillow", "SQLite"]
                mock_roadmap = {
                    "identified_requirements": [
                        "Image file upload, validation, and standard preprocessing pipeline (resize, normalize)",
                        "Trained Convolutional Neural Network (CNN / MobileNet) for multi-class image classification",
                        "Confidence score computation and remedy/advice suggestion display",
                        "Lightweight local inference REST endpoints with error handling"
                    ],
                    "suggested_tech_stack": tech_stack,
                    "stack_rationale": "Retained the student's core stack preference while supplementing with React (Vite) for the frontend interface, FastAPI for asynchronous model serving, and SQLite for lightweight scan history persistence.",
                    "project_summary": "Computer vision classification system for automated image diagnosis using deep learning CNN models and web-based reporting.",
                    "recommended_architecture": "FastAPI backend running PyTorch CNN inference + React Vite frontend with drag-and-drop image upload + SQLite for scan history.",
                    "epics": [
                        {"name": "Image Ingestion & Preprocessing", "description": "Handle client image uploads, resizing, and tensor transformation"},
                        {"name": "Deep Learning Inference Engine", "description": "Load pre-trained weights and run forward-pass classification"},
                        {"name": "Diagnosis & Analytics API", "description": "Return predicted classes, confidence probabilities, and treatment tips"},
                        {"name": "Interactive Image Diagnosis UI", "description": "Upload preview, progress indicators, and visual diagnosis report"}
                    ],
                    "tasks": [
                        {
                            "title": "Implement Image Upload & Validation Pipeline",
                            "description": "Accept PNG/JPG uploads, enforce file size limits, and resize/normalize using OpenCV/PIL.",
                            "epic_name": "Image Ingestion & Preprocessing",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/image-preprocessing"
                        },
                        {
                            "title": "Integrate PyTorch Pre-trained Model Inference",
                            "description": "Load trained MobileNet/ResNet model and execute image classification inference.",
                            "epic_name": "Deep Learning Inference Engine",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/model-inference"
                        },
                        {
                            "title": "Build Prediction Results API Endpoint",
                            "description": "Construct JSON endpoint returning top-K predicted classes with softmax probability scores.",
                            "epic_name": "Diagnosis & Analytics API",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/prediction-api"
                        },
                        {
                            "title": "Build Interactive Scan & Results Dashboard",
                            "description": "Create upload dropzone, image preview, confidence gauge meter, and recommendation cards.",
                            "epic_name": "Interactive Image Diagnosis UI",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/diagnosis-ui"
                        }
                    ]
                }
                return json.dumps(mock_roadmap)

            # NLP / Text Matching / Semantic Intelligence / Knowledge Graphs / Speech
            elif any(k in project_content for k in ["resume", "matcher", "nlp", "text", "embedding", "semantic", "sentiment", "spam", "summariz", "qa", "rag", "jd", "job", "language", "speech", "graph"]):
                is_c_mismatch = user_stack and any(s.strip().lower() in ["c", "c++", "cpp", "assembly"] for s in user_stack)
                if is_c_mismatch:
                    tech_stack = ["Python (FastAPI)", "C (Native Audio DSP / CFFI)", "faster-whisper / PyTorch", "spaCy & NetworkX", "React (Vite)", "SQLite"]
                    stack_rationale = (
                        "⚠️ Architectural Advisory: Building speech NLP, LLM summarization, and knowledge graph generation in pure C introduces severe development bottlenecks, including manual string/memory management, lack of turnkey graph visualizers (like NetworkX), and high risk of semester timeline slippage. We strongly recommend the industry-standard stack (Python with FastAPI, spaCy/NetworkX, and faster-whisper). As a viable hybrid architecture, C is isolated for low-level audio DSP/FFT routines via CFFI, while Python orchestrates the NLP and graph generation pipeline."
                    )
                else:
                    tech_stack = user_stack or ["React (Vite)", "FastAPI (Python)", "Sentence-Transformers (all-MiniLM-L6-v2)", "FAISS / ChromaDB (local)", "PyPDF2 / pdfplumber", "SQLite"]
                    stack_rationale = "Built upon the user's foundation by incorporating Sentence-Transformers for semantic embeddings, FAISS/ChromaDB for local vector similarity retrieval, and React (Vite) for the dynamic skill gap visualizer."

                mock_roadmap = {
                    "identified_requirements": [
                        "Document & speech text extraction and cleaning pipeline",
                        "Semantic text embeddings & entity graph generation",
                        "Fast local vector search and relationship ranking engine",
                        "Interactive student dashboard with summary metrics and graph visualizer"
                    ],
                    "suggested_tech_stack": tech_stack,
                    "stack_rationale": stack_rationale,
                    "project_summary": "Intelligent text processing & semantic matching platform leveraging pre-trained sentence transformer embeddings and local vector indexing.",
                    "recommended_architecture": "FastAPI async REST backend with Sentence-Transformers + React (Vite) UI + local FAISS vector indexing and SQLite metadata store.",
                    "epics": [
                        {"name": "Document Parsing & Preprocessing", "description": "Extract structured text from resumes and job descriptions"},
                        {"name": "Semantic Vector Embedding Engine", "description": "Generate dense vector embeddings using local transformer models"},
                        {"name": "Similarity & Ranking API", "description": "Calculate cosine similarity and highlight missing keywords/skills"},
                        {"name": "Student Matcher Dashboard", "description": "Interactive visualizer for match scores and actionable recommendations"}
                    ],
                    "tasks": [
                        {
                            "title": "Build Document Text Extractor",
                            "description": "Implement file upload and text parser using pdfplumber and PyPDF2 for PDF and DOCX files.",
                            "epic_name": "Document Parsing & Preprocessing",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/doc-parser"
                        },
                        {
                            "title": "Set Up Sentence-Transformers Embedding Pipeline",
                            "description": "Load all-MiniLM-L6-v2 model in FastAPI to convert text sections into 384-dimensional dense vectors.",
                            "epic_name": "Semantic Vector Embedding Engine",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/embedding-engine"
                        },
                        {
                            "title": "Implement Cosine Similarity & Skill Gap Scorer",
                            "description": "Compute vector similarity scores and extract unmatched required qualifications using regex/spaCy.",
                            "epic_name": "Similarity & Ranking API",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/matching-algorithm"
                        },
                        {
                            "title": "Create Match Result & Skill Breakdown UI",
                            "description": "Build responsive React components to display overall match percentage, strengths, and missing skills.",
                            "epic_name": "Student Matcher Dashboard",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/results-dashboard"
                        }
                    ]
                }
                return json.dumps(mock_roadmap)

            # Recommender / Real-time / Interactive
            elif any(k in project_content for k in ["recommend", "movie", "product", "music", "collaborative", "chat", "chatbot", "socket", "realtime", "live"]):
                tech_stack = user_stack or ["React (Vite)", "FastAPI (with WebSockets)", "PostgreSQL / SQLite", "Scikit-learn / Surprise", "Tailwind CSS"]
                mock_roadmap = {
                    "identified_requirements": [
                        "User interaction matrix and collaborative/content-based filtering engine",
                        "Real-time event handling using WebSockets for instant updates",
                        "User preference history and session storage in relational database",
                        "Interactive recommendation feed with rating feedback loop"
                    ],
                    "suggested_tech_stack": tech_stack,
                    "stack_rationale": "Confirmed user technology preferences and paired them with FastAPI WebSockets for live feedback synchronization, Scikit-learn for matrix factorization recommendation, and PostgreSQL for relational preference logging.",
                    "project_summary": "Interactive recommendation and real-time interaction platform providing personalized item suggestions based on user preference history.",
                    "recommended_architecture": "FastAPI server with WebSocket handlers + React UI + SQLite/PostgreSQL interaction database + Scikit-learn recommendation matrix.",
                    "epics": [
                        {"name": "Interaction & Preference Data Layer", "description": "Store and query user ratings, reviews, and session preferences"},
                        {"name": "Recommendation Algorithm Engine", "description": "Implement matrix factorization / nearest neighbor recommendation models"},
                        {"name": "Real-time Event & Socket Manager", "description": "Live WebSocket communication for interactive updates"},
                        {"name": "Personalized Feed & Rating Dashboard", "description": "Interactive cards, star ratings, and recommendation filters"}
                    ],
                    "tasks": [
                        {
                            "title": "Design User Rating & Interaction Schema",
                            "description": "Implement database tables for users, catalog items, ratings, and interaction logs.",
                            "epic_name": "Interaction & Preference Data Layer",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/interaction-schema"
                        },
                        {
                            "title": "Implement Collaborative Recommendation Scorer",
                            "description": "Train item-item collaborative filtering model using cosine similarity on user rating vectors.",
                            "epic_name": "Recommendation Algorithm Engine",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/recommender-engine"
                        },
                        {
                            "title": "Set Up WebSocket Live Channel",
                            "description": "Create FastAPI WebSocket endpoint for instant interaction broadcasts and feedback collection.",
                            "epic_name": "Real-time Event & Socket Manager",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/websocket-channel"
                        },
                        {
                            "title": "Build Dynamic Recommendation UI Feed",
                            "description": "Create responsive React view with item carousels, instant 1-5 star rating buttons, and filter chips.",
                            "epic_name": "Personalized Feed & Rating Dashboard",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/recommendation-feed"
                        }
                    ]
                }
                return json.dumps(mock_roadmap)

            # Standard Full-stack CRUD / Management / Dashboard / Tracker
            else:
                tech_stack = user_stack or ["React (Vite)", "Tailwind CSS", "FastAPI or Express.js", "SQLite / PostgreSQL", "Chart.js"]
                mock_roadmap = {
                    "identified_requirements": [
                        "Relational data schema with entity relationships and foreign key constraints",
                        "JWT user authentication and role-based access control",
                        "Responsive analytics charts and category aggregation metrics",
                        "Standard full-stack CRUD operations with zero unnecessary ML complexity"
                    ],
                    "suggested_tech_stack": tech_stack,
                    "stack_rationale": "Preserved the user's core selections while completing the full stack with React (Vite) & Tailwind CSS for a modern responsive interface, SQLite/PostgreSQL for relational persistence, and Chart.js for visualization.",
                    "project_summary": "Full-stack web application with responsive dashboard, robust relational database storage, and real-time category visualization.",
                    "recommended_architecture": "FastAPI REST API server + React (Vite) & Tailwind CSS frontend + SQLite database + Chart.js data visualization.",
                    "epics": [
                        {"name": "Database Models & Authentication", "description": "Set up relational database tables, password hashing, and JWT tokens"},
                        {"name": "Core CRUD REST Services", "description": "Create, read, update, and delete endpoints with validation"},
                        {"name": "Analytics & Metrics Aggregator", "description": "Compute summary metrics, category totals, and monthly trends"},
                        {"name": "Responsive Web Dashboard", "description": "Interactive data tables, filter search, and visual chart components"}
                    ],
                    "tasks": [
                        {
                            "title": "Design Database Models & JWT Auth",
                            "description": "Implement SQL models for users, records, and categories with JWT security.",
                            "epic_name": "Database Models & Authentication",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/db-auth"
                        },
                        {
                            "title": "Build REST CRUD Endpoints",
                            "description": "Implement FastAPI routes for managing entries with pagination and search filters.",
                            "epic_name": "Core CRUD REST Services",
                            "sprint_name": "Sprint 1",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/crud-api"
                        },
                        {
                            "title": "Implement Analytics Aggregation Pipeline",
                            "description": "Create backend summary endpoints returning aggregated statistics for charts.",
                            "epic_name": "Analytics & Metrics Aggregator",
                            "sprint_name": "Sprint 2",
                            "priority": "MEDIUM",
                            "git_branch_suggestion": "feature/analytics-api"
                        },
                        {
                            "title": "Build Interactive Chart Dashboard",
                            "description": "Construct React dashboard with Chart.js line and doughnut charts, and filterable data tables.",
                            "epic_name": "Responsive Web Dashboard",
                            "sprint_name": "Sprint 2",
                            "priority": "HIGH",
                            "git_branch_suggestion": "feature/dashboard-ui"
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
        return GeminiLLMProvider(settings.GEMINI_API_KEY, model=getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.6-flash"))
    
    if settings.LLM_PROVIDER == "mock":
        return MockLLMProvider()

    # Crash loudly if the .env is missing the key
    raise ValueError("GEMINI_API_KEY is missing or LLM_PROVIDER is not set to 'gemini' in your .env file!")
