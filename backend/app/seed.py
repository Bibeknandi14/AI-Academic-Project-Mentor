import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
import uuid
from datetime import datetime, timedelta

from app.db.session import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.commit import CommitLog
from app.models.chat import ChatMessage

async def seed():
    print("[INIT] Initializing Database Schema & Seeding Dummy Data...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Create Users
        student = User(
            id="user-student-1",
            email="student@univ.edu",
            hashed_password=get_password_hash("student123"),
            full_name="Alex Student",
            role=UserRole.STUDENT,
            github_username="alex-student",
            assigned_mentor_id="user-mentor-1"
        )
        mentor = User(
            id="user-mentor-1",
            email="mentor@univ.edu",
            hashed_password=get_password_hash("mentor123"),
            full_name="Dr. Sarah Mentor",
            role=UserRole.MENTOR,
            github_username="sarah-mentor",
            mentor_code="MNT-DEMO-01"
        )
        db.add_all([student, mentor])

        # Create Sample Projects
        p1_id = "proj-ai-mentor-1"
        project1 = Project(
            id=p1_id,
            title="AI Guided Academic Progress Tracker",
            description="3-Pillar platform with AI Planning, GitHub auto commit tracking, and context-injected mentorship.",
            github_repo="alex-student/ai-academic-mentor",
            mentor_id=mentor.id
        )

        p2_id = "proj-smart-ecommerce"
        project2 = Project(
            id=p2_id,
            title="Smart Campus E-Commerce Portal",
            description="Peer-to-peer textbook and project hardware marketplace for university students.",
            github_repo="alex-student/campus-ecommerce",
            mentor_id=mentor.id
        )
        db.add_all([project1, project2])

        # Add Project Members
        db.add(ProjectMember(id=str(uuid.uuid4()), project_id=p1_id, user_id=student.id, role="OWNER"))
        db.add(ProjectMember(id=str(uuid.uuid4()), project_id=p2_id, user_id=student.id, role="OWNER"))

        # Create Tasks for Project 1
        t1 = Task(
            id="task-101",
            project_id=p1_id,
            title="Set up DB Schemas & JWT Auth",
            description="Implement SQLAlchemy User, Project, Task models and JWT token login endpoint.",
            epic_name="Architecture & Auth",
            sprint_name="Sprint 1",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            assigned_user_id=student.id,
            git_branch="feature/auth-db"
        )
        t2 = Task(
            id="task-102",
            project_id=p1_id,
            title="Build React Kanban Board",
            description="Interactive drag-and-drop task status board supporting TODO, IN_PROGRESS, IN_REVIEW, DONE.",
            epic_name="UI & Kanban",
            sprint_name="Sprint 1",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assigned_user_id=student.id,
            git_branch="feature/kanban-ui"
        )
        t3 = Task(
            id="task-103",
            project_id=p1_id,
            title="GitHub Commit Tracking Engine",
            description="Fetch repo commit logs via REST API, parse commit messages, and auto-advance task status.",
            epic_name="GitHub Engine",
            sprint_name="Sprint 2",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assigned_user_id=student.id,
            git_branch="feature/github-sync"
        )
        t4 = Task(
            id="task-104",
            project_id=p1_id,
            title="Context-Injected AI Mentorship Chat",
            description="RAG chat endpoint fetching active task + top commits context before calling LLM.",
            epic_name="AI Mentorship",
            sprint_name="Sprint 2",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assigned_user_id=student.id,
            git_branch="feature/ai-chat"
        )
        db.add_all([t1, t2, t3, t4])

        # Create Tasks for Project 2 (At Risk example)
        t_p2 = Task(
            id="task-201",
            project_id=p2_id,
            title="Backend Payment Gateway Integration",
            description="Stripe Connect setup for student transactions.",
            epic_name="Payments",
            sprint_name="Sprint 1",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assigned_user_id=student.id
        )
        db.add(t_p2)

        # Create Commits for Project 1
        c1 = CommitLog(
            id=str(uuid.uuid4()),
            project_id=p1_id,
            task_id=t1.id,
            commit_hash="a8f3e21",
            author_name="Alex Student",
            message="feat: set up database schemas and auth system",
            commit_date=datetime.utcnow() - timedelta(days=1),
            url=f"https://github.com/alex-student/ai-academic-mentor/commit/a8f3e21"
        )
        c2 = CommitLog(
            id=str(uuid.uuid4()),
            project_id=p1_id,
            task_id=t2.id,
            commit_hash="c4d9e02",
            author_name="Alex Student",
            message="feat: implement kanban board component and status state updates",
            commit_date=datetime.utcnow() - timedelta(hours=5),
            url=f"https://github.com/alex-student/ai-academic-mentor/commit/c4d9e02"
        )
        db.add_all([c1, c2])

        # Create Initial Chat Message
        chat1 = ChatMessage(
            id=str(uuid.uuid4()),
            project_id=p1_id,
            user_id=student.id,
            task_id=t2.id,
            sender="USER",
            message="How do I connect the task status drop target with FastAPI back-end state update?",
            context_used={
                "active_task": {"title": "Build React Kanban Board", "status": "IN_PROGRESS"},
                "recent_commits": [{"hash": "c4d9e02", "message": "feat: implement kanban board component"}]
            }
        )
        chat2 = ChatMessage(
            id=str(uuid.uuid4()),
            project_id=p1_id,
            user_id=student.id,
            task_id=t2.id,
            sender="AI",
            message="### Guidance for Task: Build React Kanban Board\n\nIn your React Kanban component, when a user drops a card into a new column, trigger a `PATCH /api/tasks/{taskId}` request passing `status: 'IN_PROGRESS'` or `status: 'DONE'`. Your backend `tasks.py` router will update the task in SQLite/PostgreSQL and return the updated task object.",
            context_used={
                "active_task": {"title": "Build React Kanban Board", "status": "IN_PROGRESS"},
                "recent_commits": [{"hash": "c4d9e02", "message": "feat: implement kanban board component"}]
            }
        )
        db.add_all([chat1, chat2])

        await db.commit()
        print("[SUCCESS] Database successfully populated with realistic student & mentor dummy data!")

if __name__ == "__main__":
    asyncio.run(seed())
