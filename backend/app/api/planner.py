import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.planner import RoadmapGenerationInput, RoadmapGenerationOutput
from app.services.llm_service import get_llm_provider

router = APIRouter(prefix="/planner", tags=["AI Roadmap Planner"])

PLANNER_SYSTEM_INSTRUCTION = (
    "You are an expert academic software mentor and software architect for B.Tech AI/ML and Computer Science university students.\n"
    "Your role is to evaluate student project ideas, identify their true technical requirements, and generate a tailored, realistic Agile project roadmap and tech stack.\n\n"
    "CRITICAL GUIDELINES & NEGATIVE CONSTRAINTS:\n"
    "1. Tailored Stacks (No Boilerplate Defaults): Do NOT default to the same generic stack (e.g. React + FastAPI + PostgreSQL + RAG) for every project. Base your stack choice strictly on the specific technical needs of this project. A simple app should get a simple, lightweight stack; only add complexity (vector DBs, NLP embeddings, CV models, async workers) when the project idea genuinely requires it.\n"
    "2. Student Feasibility: Keep all recommended tools and libraries realistic for solo or small-team university students working with free-tier / local tools (e.g., SQLite, PostgreSQL, ChromaDB, FAISS, Streamlit, React, FastAPI, Flask, Vite, Scikit-learn, PyTorch, OpenCV). Never recommend heavy enterprise infrastructure (e.g. Kafka clusters, Kubernetes, distributed Spark, dedicated GPU cloud fleets) unless the student explicitly asks.\n"
    "3. Grounded Selection: First evaluate and state the project's technical requirements in `identified_requirements` before choosing the `suggested_tech_stack`.\n\n"
    "=== EXAMPLES FOR FORMATTING REFERENCE ONLY (DO NOT COPY CONTENT) ===\n"
    "The following examples are STRICTLY to show you the expected JSON structure. "
    "DO NOT use FAISS, NLP, Computer Vision, or WebSockets unless the student's specific project description explicitly requires them.\n\n"
    "Example 1: Basic CRUD / Dashboard / Management\n"
    "Project: 'Student Expense Tracker with Category Visualizations'\n"
    "Identified Requirements: ['Relational data storage for transactions & categories', 'User authentication and session management', 'Responsive charts for monthly expense trends', 'No AI/ML required — standard CRUD operations']\n"
    "Suggested Tech Stack: ['React (Vite)', 'Tailwind CSS', 'FastAPI or Express.js', 'SQLite / PostgreSQL', 'Chart.js']\n\n"
    "Example 2: NLP / Text Matching / Semantic Analysis\n"
    "Project: 'Resume & Job Description Skill Gap Matcher'\n"
    "Identified Requirements: ['PDF/DOCX text extraction', 'Semantic text embeddings for cosine similarity matching', 'Fast local vector search or ranking', 'Interactive dashboard for match score and skill gap highlights']\n"
    "Suggested Tech Stack: ['React (Vite)', 'FastAPI (Python)', 'Sentence-Transformers (all-MiniLM-L6-v2)', 'FAISS / ChromaDB (local)', 'PyPDF2 / pdfplumber', 'SQLite']\n\n"
    "Example 3: Computer Vision / Image Classification\n"
    "Project: 'Plant Leaf Disease Classifier from Leaf Images'\n"
    "Identified Requirements: ['Image file upload & preprocessing pipeline', 'Trained Convolutional Neural Network (CNN / MobileNet / ResNet) for multi-class classification', 'Confidence score visualization and remedy suggestion display', 'Lightweight local inference backend']\n"
    "Suggested Tech Stack: ['React (Vite) or Streamlit', 'FastAPI / Flask', 'PyTorch / torchvision (or TensorFlow/Keras)', 'OpenCV / PIL', 'SQLite (for scan history)']\n\n"
    "Example 4: Real-time Interaction / Recommendation\n"
    "Project: 'Collaborative Movie Recommender & Discussion Room'\n"
    "Identified Requirements: ['Collaborative filtering / matrix factorization or content-based recommendation algorithm', 'Live chat / discussion room using WebSockets (not heavy message brokers)', 'User rating and interaction history database']\n"
    "Suggested Tech Stack: ['React (Vite)', 'FastAPI (with WebSockets)', 'PostgreSQL / SQLite', 'Surprise / Scikit-learn', 'Tailwind CSS']"
)

@router.post("/generate", response_model=RoadmapGenerationOutput)
async def generate_roadmap(
    input_data: RoadmapGenerationInput,
    current_user: User = Depends(get_current_user)
):
    llm = get_llm_provider()
    
    if input_data.tech_stack and len(input_data.tech_stack) > 0:
        tech_context = (
            f"Student Preferred Tech Stack: {', '.join(input_data.tech_stack)}\n"
            f"- Respect and build the project architecture and sprint tasks around this preferred tech stack.\n"
            f"- In `identified_requirements`, note how their preferred stack addresses the project needs.\n"
            f"- Include these in `suggested_tech_stack` along with any essential supporting libraries or tools."
        )
    else:
        tech_context = (
            f"Student Preferred Tech Stack: None provided (Student wants AI recommendation).\n"
            f"- First, identify the exact technical requirements (e.g. CV vs NLP vs tabular vs CRUD vs real-time) in `identified_requirements`.\n"
            f"- Next, select a lean, modern, student-feasible stack in `suggested_tech_stack` directly matching those requirements."
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
        f"2. Step 2: In `suggested_tech_stack`, recommend a tailored, realistic tech stack based directly on those requirements (avoid boilerplate defaults).\n"
        f"3. Step 3: Provide a clear `project_summary` and `recommended_architecture` explaining system design.\n"
        f"4. Step 4: Divide the project into logical epics and actionable, concrete sprint tasks split across sprints with realistic git branch suggestions and priorities."
    )
    
    try:
        output = await llm.generate_structured_json(
            prompt=prompt,
            response_schema=RoadmapGenerationOutput,
            system_instruction=PLANNER_SYSTEM_INSTRUCTION
        )
        return output
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {str(e)}"
        )

@router.post("/convert-to-project", status_code=status.HTTP_201_CREATED)
async def convert_roadmap_to_project(
    roadmap_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
