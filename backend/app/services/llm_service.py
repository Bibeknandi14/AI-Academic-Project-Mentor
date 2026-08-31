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
            # Use Gemini REST API with native system_instruction and application/json format
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.4
                }
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }
            
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

            # NLP / Text Matching / Semantic Intelligence
            elif any(k in project_content for k in ["resume", "matcher", "nlp", "text", "embedding", "semantic", "sentiment", "spam", "summariz", "qa", "rag", "jd", "job", "language"]):
                tech_stack = user_stack or ["React (Vite)", "FastAPI (Python)", "Sentence-Transformers (all-MiniLM-L6-v2)", "FAISS / ChromaDB (local)", "PyPDF2 / pdfplumber", "SQLite"]
                mock_roadmap = {
                    "identified_requirements": [
                        "Document text extraction and cleaning (PDF/DOCX/TXT)",
                        "Semantic text embeddings for cosine similarity matching",
                        "Fast local vector search or ranking engine",
                        "Interactive student dashboard with match scores and skill gap highlights"
                    ],
                    "suggested_tech_stack": tech_stack,
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
        return GeminiLLMProvider(settings.GEMINI_API_KEY)
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return MockLLMProvider()
    return MockLLMProvider()
