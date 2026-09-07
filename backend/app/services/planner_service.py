import uuid
import logging
from typing import Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.planner import RoadmapGenerationInput, RoadmapGenerationOutput, PlannedEpic, PlannedTask
from app.services.llm_service import get_llm_provider, GeminiQuotaExceededError

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = (
    "You are an expert academic software mentor and lead software architect for university computer science and AI/ML engineering students.\n"
    "Your role is to evaluate student project ideas, identify their true technical requirements, and generate a tailored, realistic Agile project roadmap, architecture design, and comprehensive layered tech stack.\n\n"
    "CRITICAL ARCHITECTURAL CONSTRAINTS & EDUCATIONAL SOFTWARE MENTORSHIP:\n"
    "1. Explicit Architectural Advisory & Friction Warning on Domain Mismatch:\n"
    "   - When a student provides a language or tool with a severe architectural mismatch for the domain (for example, choosing pure C or Assembly for an LLM summarizer, speech transcription NLP pipeline, or semantic knowledge graph generator):\n"
    "     a. In `stack_rationale`, LEAD IMMEDIATELY with an explicit advisory starting with: '⚠️ Architectural Advisory:'.\n"
    "     b. Detail specific engineering bottlenecks: explicitly call out friction such as manual string manipulation & pointer memory management, lack of turnkey native NLP/graph packages (e.g. absence of tokenizers, embedding models, graph visualizers), and the extreme risk of semester timeline slippage for a student project.\n"
    "     c. Explicitly propose the modern industry-standard stack (such as Python with FastAPI, spaCy/NetworkX, and faster-whisper/Sentence-Transformers) as the primary recommendation for the domain.\n"
    "     d. Provide a sensible default architecture and viable hybrid alternative: explain how production systems isolate lower-level languages (e.g. C/C++ or Rust for native audio DSP / FFT / custom kernels via CFFI/pybind11) while orchestrating NLP pipelines and web APIs in Python.\n"
    "     e. CRITICAL FOR ROADMAP GENERATION: Ensure the generated `epics`, `tasks`, and `recommended_architecture` use the workable modern standard stack (or sensible hybrid architecture), ensuring the student is NEVER handed an unexecutable, unrealistic pure-C roadmap for high-level NLP/graph tasks.\n\n"
    "2. Mandatory Tech Stack Completion & Layer Categorization:\n"
    "   - When a student provides partial input (such as only 'Python', or 'React', or 'PyTorch & SQLite'):\n"
    "     a. Retain their input as part of the architecture.\n"
    "     b. Automatically infer and generate all missing layers (Client/GUI, Backend/API, Database/Persistence, and Domain/ML libraries).\n"
    "     c. If no domain mismatch exists, explain in `stack_rationale` how the supplementary tools complete the full-stack architecture.\n\n"
    "3. Student Feasibility & No Unnecessary Complexity:\n"
    "   - Recommend free, local, or lightweight student-friendly tools (e.g., SQLite, PostgreSQL, ChromaDB, FAISS, Streamlit, React, FastAPI, Flask, Vite, Scikit-learn, PyTorch, OpenCV).\n"
    "   - Never recommend enterprise-scale cluster infrastructure (e.g. Kafka clusters, Kubernetes fleets, Spark clusters) unless explicitly requested.\n\n"
    "4. Grounded Selection & Structured JSON Output:\n"
    "   - Step 1: In `identified_requirements`, list 2-4 specific technical requirements identified from the idea.\n"
    "   - Step 2: In `suggested_tech_stack`, include a complete workable stack covering all tiers (Client/GUI, Backend/API, Persistence, and ML/NLP tools).\n"
    "   - Step 3: In `stack_rationale`, provide the explicit advisory warning (if mismatch detected) or comprehensive layer rationale.\n"
    "   - Step 4: In `recommended_architecture` and `project_summary`, provide a clean, executable system design.\n"
    "   - Step 5: In `epics` and `tasks`, construct actionable, concrete sprint tasks across sprints with git branch suggestions and priorities."
)

class PlannerService:
    @classmethod
    def _build_fallback_roadmap(
        cls,
        input_data: RoadmapGenerationInput,
        error_reason: str = ""
    ) -> RoadmapGenerationOutput:
        """Construct a high-quality domain-tailored starter roadmap when the LLM service is temporarily unreachable."""
        combined_text = f"{input_data.idea_title} {input_data.idea_description}".lower()
        user_stack = input_data.tech_stack or []
        user_stack_lower = [s.lower() for s in user_stack]
        is_c_mismatch = any(s in ["c", "c++", "cpp", "assembly"] for s in user_stack_lower)

        # 1. Computer Vision / Image Intelligence
        if any(k in combined_text for k in ["image", "vision", "plant", "disease", "face", "camera", "opencv", "cnn", "yolo", "leaf", "medical", "scan", "photo", "detection"]):
            stack = user_stack if user_stack else ["React (Vite)", "FastAPI", "PyTorch / torchvision", "OpenCV / Pillow", "SQLite"]
            rationale = (
                "Constructed a complete computer vision pipeline combining client image ingestion, "
                "FastAPI asynchronous inference endpoints, PyTorch CNN model evaluation, and SQLite persistence."
            )
            reqs = [
                "Image ingestion & validation pipeline (multi-format upload, resizing, tensor normalization)",
                "Deep learning CNN / transfer learning model for inference & classification",
                "REST API serving model predictions with confidence scores and error handling",
                "Interactive frontend dashboard with upload preview, confidence gauges, and results report"
            ]
            summary = f"Computer vision classification system for {input_data.idea_title} using deep learning and web reporting."
            architecture = "FastAPI backend running PyTorch CNN inference + React Vite frontend with drag-and-drop image upload + SQLite for scan history."
            epics = [
                PlannedEpic(name="Image Ingestion & Preprocessing", description="Handle client image uploads, resizing, and tensor transformation"),
                PlannedEpic(name="Deep Learning Inference Engine", description="Load pre-trained weights and run forward-pass classification"),
                PlannedEpic(name="Diagnosis & Analytics API", description="Return predicted classes, confidence probabilities, and treatment tips"),
                PlannedEpic(name="Interactive Results Dashboard UI", description="Upload preview, progress indicators, and visual diagnosis report")
            ]
            tasks = [
                PlannedTask(title="Implement Image Upload & Validation Pipeline", description="Accept PNG/JPG uploads, enforce file size limits, and resize/normalize using OpenCV/PIL.", epic_name="Image Ingestion & Preprocessing", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/image-preprocessing"),
                PlannedTask(title="Integrate PyTorch Model Inference", description="Load trained CNN model and execute image classification inference.", epic_name="Deep Learning Inference Engine", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/model-inference"),
                PlannedTask(title="Build Prediction Results API Endpoint", description="Construct JSON endpoint returning top-K predicted classes with softmax probability scores.", epic_name="Diagnosis & Analytics API", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/prediction-api"),
                PlannedTask(title="Build Interactive Scan & Results Dashboard", description="Create upload dropzone, image preview, confidence gauge meter, and recommendation cards.", epic_name="Interactive Results Dashboard UI", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/diagnosis-ui")
            ]

        # 2. NLP / Semantic Search / Text Processing / Speech / Knowledge Graphs
        elif any(k in combined_text for k in ["resume", "matcher", "nlp", "text", "embedding", "semantic", "sentiment", "spam", "summariz", "qa", "rag", "jd", "job", "language", "speech", "graph", "audio"]):
            if is_c_mismatch:
                stack = ["Python (FastAPI)", "C (Native Audio DSP / CFFI)", "faster-whisper / PyTorch", "spaCy & NetworkX", "React (Vite)", "SQLite"]
                rationale = (
                    "⚠️ Architectural Advisory: Building speech NLP and semantic graph generation in pure C introduces severe bottlenecks (manual memory/string management, lack of turnkey NLP packages). Recommended standard is Python (FastAPI + spaCy/Sentence-Transformers) with C isolated for native audio DSP/FFI routines."
                )
            else:
                stack = user_stack if user_stack else ["React (Vite)", "FastAPI (Python)", "Sentence-Transformers (all-MiniLM-L6-v2)", "FAISS / ChromaDB", "PyPDF2 / pdfplumber", "SQLite"]
                rationale = (
                    "Constructed an intelligent semantic NLP architecture using Sentence-Transformers for dense vector embeddings, "
                    "FAISS for vector retrieval, and FastAPI + React for the interactive visualizer."
                )
            reqs = [
                "Document & speech text extraction and preprocessing pipeline",
                "Semantic text embeddings & dense vector representation",
                "Fast local vector similarity search and relationship ranking engine",
                "Interactive student dashboard with summary metrics and actionable visualizer"
            ]
            summary = f"Intelligent text processing and semantic matching platform for {input_data.idea_title}."
            architecture = "FastAPI async REST backend with Sentence-Transformers + React (Vite) UI + local FAISS vector indexing and SQLite metadata store."
            epics = [
                PlannedEpic(name="Document Parsing & Preprocessing", description="Extract structured text from uploaded documents and inputs"),
                PlannedEpic(name="Semantic Vector Embedding Engine", description="Generate dense vector embeddings using local transformer models"),
                PlannedEpic(name="Similarity & Ranking API", description="Calculate cosine similarity and highlight missing keywords/qualifications"),
                PlannedEpic(name="Student Matcher Dashboard", description="Interactive visualizer for match scores and actionable recommendations")
            ]
            tasks = [
                PlannedTask(title="Build Document Text Extractor", description="Implement file upload and text parser using pdfplumber and PyPDF2.", epic_name="Document Parsing & Preprocessing", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/doc-parser"),
                PlannedTask(title="Set Up Sentence-Transformers Pipeline", description="Load all-MiniLM-L6-v2 model in FastAPI to convert text into dense vectors.", epic_name="Semantic Vector Embedding Engine", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/embedding-engine"),
                PlannedTask(title="Implement Similarity & Ranking API", description="Compute vector similarity scores and return ranked match percentages.", epic_name="Similarity & Ranking API", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/matching-algorithm"),
                PlannedTask(title="Create Match Result Breakdown UI", description="Build responsive React components displaying overall match scores and missing skills.", epic_name="Student Matcher Dashboard", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/results-dashboard")
            ]

        # 3. Real-time / Recommender / Interactive
        elif any(k in combined_text for k in ["recommend", "movie", "product", "music", "collaborative", "chat", "chatbot", "socket", "realtime", "live", "message"]):
            stack = user_stack if user_stack else ["React (Vite)", "FastAPI (WebSockets)", "PostgreSQL / SQLite", "Scikit-learn", "Tailwind CSS"]
            rationale = (
                "Configured a real-time reactive architecture with FastAPI WebSockets for live message dispatch, "
                "Scikit-learn for recommendation matrix computation, and relational storage for interaction histories."
            )
            reqs = [
                "User interaction matrix and collaborative/content-based filtering engine",
                "Real-time event handling using WebSockets for instant updates",
                "User preference history and session storage in relational database",
                "Interactive recommendation feed with rating feedback loop"
            ]
            summary = f"Interactive real-time platform for {input_data.idea_title}."
            architecture = "FastAPI server with WebSocket handlers + React UI + SQLite/PostgreSQL interaction database + Scikit-learn recommendation matrix."
            epics = [
                PlannedEpic(name="Interaction & Preference Data Layer", description="Store and query user ratings, reviews, and session preferences"),
                PlannedEpic(name="Recommendation Algorithm Engine", description="Implement matrix factorization / nearest neighbor recommendation models"),
                PlannedEpic(name="Real-time Event & Socket Manager", description="Live WebSocket communication for interactive updates"),
                PlannedEpic(name="Personalized Feed & Rating Dashboard", description="Interactive cards, star ratings, and recommendation filters")
            ]
            tasks = [
                PlannedTask(title="Design User Rating & Interaction Schema", description="Implement database tables for users, catalog items, ratings, and logs.", epic_name="Interaction & Preference Data Layer", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/interaction-schema"),
                PlannedTask(title="Implement Recommendation Scorer", description="Train item collaborative filtering model using cosine similarity.", epic_name="Recommendation Algorithm Engine", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/recommender-engine"),
                PlannedTask(title="Set Up WebSocket Live Channel", description="Create FastAPI WebSocket endpoint for instant interaction broadcasts.", epic_name="Real-time Event & Socket Manager", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/websocket-channel"),
                PlannedTask(title="Build Dynamic Recommendation UI Feed", description="Create responsive React view with item cards and instant rating actions.", epic_name="Personalized Feed & Rating Dashboard", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/recommendation-feed")
            ]

        # 4. Standard Full-Stack Web Application / CRUD / Dashboard
        else:
            stack = user_stack if user_stack else ["React (Vite)", "Tailwind CSS", "FastAPI (Python)", "SQLite / PostgreSQL", "Chart.js"]
            rationale = (
                "Curated a clean full-stack student architecture combining React & Tailwind CSS for modern UI, "
                "FastAPI for modular REST endpoints, SQLite/PostgreSQL for relational persistence, and Chart.js for analytics."
            )
            reqs = [
                "Relational data schema with entity relationships and foreign key constraints",
                "JWT user authentication and role-based access control",
                "Responsive analytics charts and category aggregation metrics",
                "Standard full-stack CRUD operations with robust input validation"
            ]
            summary = f"Full-stack web application with responsive dashboard for {input_data.idea_title}."
            architecture = "FastAPI REST API server + React (Vite) frontend + SQLite/PostgreSQL database + Chart.js data visualization."
            epics = [
                PlannedEpic(name="Database Models & Authentication", description="Set up relational database tables, password hashing, and JWT tokens"),
                PlannedEpic(name="Core CRUD REST Services", description="Create, read, update, and delete endpoints with Pydantic validation"),
                PlannedEpic(name="Analytics & Metrics Aggregator", description="Compute summary metrics, category totals, and trend statistics"),
                PlannedEpic(name="Responsive Web Dashboard", description="Interactive data tables, filter search, and visual chart components")
            ]
            tasks = [
                PlannedTask(title="Design Database Models & JWT Auth", description="Implement SQL models for users, records, and categories with JWT security.", epic_name="Database Models & Authentication", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/db-auth"),
                PlannedTask(title="Build REST CRUD Endpoints", description="Implement FastAPI routes for managing entries with pagination and search filters.", epic_name="Core CRUD REST Services", sprint_name="Sprint 1", priority="HIGH", git_branch_suggestion="feature/crud-api"),
                PlannedTask(title="Implement Analytics Aggregation Pipeline", description="Create backend summary endpoints returning aggregated statistics for charts.", epic_name="Analytics & Metrics Aggregator", sprint_name="Sprint 2", priority="MEDIUM", git_branch_suggestion="feature/analytics-api"),
                PlannedTask(title="Build Interactive Chart Dashboard", description="Construct React dashboard with Chart.js line and doughnut charts, and filterable data tables.", epic_name="Responsive Web Dashboard", sprint_name="Sprint 2", priority="HIGH", git_branch_suggestion="feature/dashboard-ui")
            ]

        # Ensure all user-selected tech items are retained in suggested_tech_stack
        if user_stack:
            existing_lower = [s.lower() for s in stack]
            for user_item in user_stack:
                if user_item.lower() not in existing_lower and not any(user_item.lower() in x for x in existing_lower):
                    stack.insert(0, user_item)

        # Prepend advisory notice if AI service was temporarily overloaded or quota exhausted
        if any(q in error_reason.lower() for q in ["quota", "resource_exhausted", "geminiquotaexceedederror"]):
            notice_prefix = "⚠️ Note: Gemini AI daily free-tier quota has been reached on this model, so a verified starter roadmap has been generated for your project. You can customize the requirements, stack, and tasks below before converting to a project.\n\n"
        else:
            notice_prefix = "⚠️ Note: Gemini AI is currently experiencing high network demand or transient timeout, so a verified starter roadmap has been generated. You can customize the requirements, stack, and tasks below before converting to a project.\n\n"
        
        final_rationale = f"{notice_prefix}{rationale}"

        return RoadmapGenerationOutput(
            identified_requirements=reqs,
            suggested_tech_stack=stack,
            stack_rationale=final_rationale,
            project_summary=summary,
            recommended_architecture=architecture,
            epics=epics,
            tasks=tasks
        )

    @classmethod
    async def generate_roadmap(
        cls,
        input_data: RoadmapGenerationInput,
        current_user: User
    ) -> RoadmapGenerationOutput:
        llm = get_llm_provider()
        
        if input_data.tech_stack and len(input_data.tech_stack) > 0:
            user_stack_str = ", ".join(input_data.tech_stack)
            tech_context = (
                f"Student Preferred Tech Stack: {user_stack_str}\n"
                f"- EDUCATIONAL MENTORSHIP & DOMAIN MISMATCH CHECK: Evaluate if [{user_stack_str}] presents severe development bottlenecks for this domain (e.g. pure C for an LLM summarizer, speech NLP, or knowledge graph generator).\n"
                f"- IF MISMATCH DETECTED: `stack_rationale` MUST start with '⚠️ Architectural Advisory:', explicitly detail the bottlenecks (manual string manipulation, memory management, lack of turnkey NLP/graph packages, timeline slip risk), recommend the production standard (Python with FastAPI, spaCy/NetworkX, faster-whisper), and describe a viable hybrid alternative (C for native audio DSP/FFI, Python for NLP).\n"
                f"- SENSIBLE WORKABLE ARCHITECTURE: Build the `suggested_tech_stack`, `epics`, and `tasks` using the workable production/hybrid stack so the student receives an executable sprint plan (never an unexecutable pure-C NLP plan).\n"
                f"- IF NO MISMATCH: Retain [{user_stack_str}], complete all missing layers (Client/GUI, Backend/API, Persistence), and explain the rationale in `stack_rationale`."
            )
        else:
            tech_context = (
                f"Student Preferred Tech Stack: None provided (Student requested full AI recommendation).\n"
                f"- Identify the exact technical requirements in `identified_requirements`.\n"
                f"- Select a complete, multi-layered, student-feasible stack (Client/GUI, Backend/API, Persistence, and auxiliary libraries) in `suggested_tech_stack`.\n"
                f"- In `stack_rationale`, write a 2-3 sentence explanation detailing why this cohesive stack was curated for the project."
            )

        prompt = (
            f"Act as a Senior Agile Project Manager and Lead Software Architect for university students.\n"
            f"Analyze the student project idea and create a structured, realistic technical sprint roadmap and architecture plan.\n\n"
            f"<STUDENT_PROJECT_TITLE>\n{input_data.idea_title}\n</STUDENT_PROJECT_TITLE>\n\n"
            f"<STUDENT_PROJECT_DESCRIPTION>\n{input_data.idea_description}\n</STUDENT_PROJECT_DESCRIPTION>\n\n"
            f"<TECH_STACK_CONTEXT>\n{tech_context}\n</TECH_STACK_CONTEXT>\n\n"
            f"<PROJECT_PARAMETERS>\n"
            f"Duration: {input_data.duration_weeks} weeks\n"
            f"Team Size: {input_data.team_size} student(s)\n"
            f"</PROJECT_PARAMETERS>\n\n"
            f"Instructions:\n"
            f"1. Step 1: In `identified_requirements`, list 2-4 specific technical requirements identified from the idea.\n"
            f"2. Step 2: In `suggested_tech_stack`, include a workable full stack (Client, Backend, Persistence, ML/Domain tools).\n"
            f"3. Step 3: In `stack_rationale`, provide the explicit advisory warning (if mismatch detected) or layer rationale.\n"
            f"4. Step 4: Provide `project_summary` and `recommended_architecture` explaining the executable system design.\n"
            f"5. Step 5: Divide the project into logical epics and actionable sprint tasks with git branches and priorities."
        )

        try:
            output = await llm.generate_structured_json(
                prompt=prompt,
                response_schema=RoadmapGenerationOutput,
                system_instruction=PLANNER_SYSTEM_PROMPT,
                timeout=120.0
            )
            
            # Post-check: ensure user stack is preserved in suggested_tech_stack if somehow omitted
            if input_data.tech_stack:
                existing_lower = [s.lower() for s in output.suggested_tech_stack]
                for user_item in input_data.tech_stack:
                    if user_item.lower() not in existing_lower and not any(user_item.lower() in x for x in existing_lower):
                        output.suggested_tech_stack.insert(0, user_item)
            
            # Post-check: ensure stack_rationale is non-empty
            if not output.stack_rationale:
                if input_data.tech_stack:
                    output.stack_rationale = (
                        f"Retained the specified preferences ({', '.join(input_data.tech_stack)}) and completed "
                        f"the architecture with complementary frontend, API, and database persistence layers."
                    )
                else:
                    output.stack_rationale = (
                        "Curated a complete, multi-tier student architecture tailored specifically to the project's "
                        "functional requirements and persistence needs."
                    )

            return output
        except Exception as e:
            logger.error(f"[PlannerService] LLM roadmap generation failed after retries: ({type(e).__name__}: {e}). Generating graceful fallback starter roadmap.", exc_info=True)
            return cls._build_fallback_roadmap(input_data, error_reason=str(e))

    @classmethod
    async def convert_to_project(
        cls,
        roadmap_data: dict,
        db: AsyncSession,
        current_user: User
    ) -> Dict[str, Any]:
        title = roadmap_data.get("idea_title") or "New AI Planned Project"
        description = roadmap_data.get("project_summary") or roadmap_data.get("idea_description")
        
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            title=title,
            description=description,
            github_repo=roadmap_data.get("github_repo")
        )
        db.add(project)

        member = ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=current_user.id,
            role="OWNER"
        )
        db.add(member)

        # Add tasks
        tasks = roadmap_data.get("tasks", [])
        created_tasks = []
        for t in tasks:
            p_val = t.get("priority", "MEDIUM").upper()
            p_enum = TaskPriority.MEDIUM
            if p_val == "HIGH":
                p_enum = TaskPriority.HIGH
            elif p_val == "LOW":
                p_enum = TaskPriority.LOW

            task = Task(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=t.get("title", "Untitled Task"),
                description=t.get("description", ""),
                epic_name=t.get("epic_name", "Core"),
                sprint_name=t.get("sprint_name", "Sprint 1"),
                status=TaskStatus.TODO,
                priority=p_enum,
                assigned_user_id=current_user.id,
                git_branch=t.get("git_branch_suggestion")
            )
            db.add(task)
            created_tasks.append(task)

        await db.commit()
        return {"project_id": project_id, "title": title, "task_count": len(created_tasks)}
