import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.project import Project
from app.models.task import Task
from app.models.commit import CommitLog
from app.models.chat import ChatMessage
from app.schemas.mentorship import MentorshipQueryInput, ChatMessageResponse, InjectedContextSummary
from app.services.llm_service import get_llm_provider

logger = logging.getLogger(__name__)

class MentorshipService:
    @classmethod
    async def process_student_query(
        cls,
        db: AsyncSession,
        user_id: str,
        query_input: MentorshipQueryInput
    ) -> ChatMessageResponse:
        # Step 1: Fetch active task from DB
        task_data = None
        if query_input.active_task_id:
            res_t = await db.execute(select(Task).where(Task.id == query_input.active_task_id))
            active_task = res_t.scalars().first()
            if active_task:
                task_data = {
                    "id": active_task.id,
                    "title": active_task.title,
                    "description": active_task.description,
                    "status": active_task.status,
                    "epic": active_task.epic_name,
                    "sprint": active_task.sprint_name,
                    "branch": active_task.git_branch
                }
        
        if not task_data:
            # Fallback to fetching any active IN_PROGRESS or TODO task
            res_any = await db.execute(
                select(Task)
                .where(Task.project_id == query_input.project_id)
                .order_by(Task.updated_at.desc())
            )
            latest_t = res_any.scalars().first()
            if latest_t:
                task_data = {
                    "id": latest_t.id,
                    "title": latest_t.title,
                    "description": latest_t.description,
                    "status": latest_t.status,
                    "epic": latest_t.epic_name,
                    "sprint": latest_t.sprint_name,
                    "branch": latest_t.git_branch
                }

        # Step 2: Fetch latest GitHub commits for project
        res_commits = await db.execute(
            select(CommitLog)
            .where(CommitLog.project_id == query_input.project_id)
            .order_by(CommitLog.commit_date.desc())
            .limit(5)
        )
        recent_commits = res_commits.scalars().all()
        commits_data = [
            {
                "hash": c.commit_hash,
                "author": c.author_name,
                "message": c.message,
                "date": c.commit_date.isoformat() if c.commit_date else ""
            }
            for c in recent_commits
        ]

        # Step 3: Fetch project title & details
        res_proj = await db.execute(select(Project).where(Project.id == query_input.project_id))
        project = res_proj.scalars().first()
        proj_title = project.title if project else "Academic Project"

        # Construct Injected Context Summary
        context_summary = InjectedContextSummary(
            active_task=task_data,
            recent_commits=commits_data,
            tech_stack=["React.js", "FastAPI", "SQLAlchemy", "SQLite/PostgreSQL"]
        )

        # Step 4: Inject fetched context into strict RAG prompt
        task_context_str = (
            f"- Title: {task_data['title']}\n"
            f"- Description: {task_data['description']}\n"
            f"- Status: {task_data['status']}\n"
            f"- Epic/Sprint: {task_data.get('epic')} / {task_data.get('sprint')}\n"
            f"- Git Branch: {task_data.get('branch') or 'main'}\n"
            if task_data else "No active task currently selected."
        )

        commit_context_str = "\n".join([
            f"- [{c['hash']}] {c['author']}: {c['message']} ({c['date']})"
            for c in commits_data
        ]) if commits_data else "No GitHub commit activity recorded yet."

        grounded_system_instruction = (
            "You are an expert AI Academic Project Mentor assisting student software engineers.\n"
            "CRITICAL REQUIREMENT: You MUST ground your answer directly in the student's CURRENT ACTIVE TASK "
            "and LATEST GITHUB COMMITS provided in the context below.\n"
            "Do NOT provide generic answers — reference their specific task objectives, tech stack, and commit state.\n"
            "Provide clean markdown, concise explanations, and actionable code snippets."
        )

        rag_prompt = (
            f"=== PROJECT METADATA ===\n"
            f"Project: {proj_title}\n\n"
            f"=== CURRENT ACTIVE TASK CONTEXT ===\n"
            f"{task_context_str}\n\n"
            f"=== RECENT GITHUB COMMITS CONTEXT ===\n"
            f"{commit_context_str}\n\n"
            f"=== STUDENT QUESTION ===\n"
            f"{query_input.question}\n\n"
            f"Please mentor the student specifically based on the task and commit context above."
        )

        # Step 5: Save user question to ChatMessage DB
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            project_id=query_input.project_id,
            user_id=user_id,
            task_id=task_data["id"] if task_data else None,
            sender="USER",
            message=query_input.question,
            context_used=context_summary.model_dump()
        )
        db.add(user_msg)

        # Step 6: Query LLM Provider with injected context
        llm = get_llm_provider()
        ai_response_text = await llm.generate_text(
            prompt=rag_prompt,
            system_instruction=grounded_system_instruction
        )

        # Step 7: Save AI answer to ChatMessage DB
        ai_msg = ChatMessage(
            id=str(uuid.uuid4()),
            project_id=query_input.project_id,
            user_id=user_id,
            task_id=task_data["id"] if task_data else None,
            sender="AI",
            message=ai_response_text,
            context_used=context_summary.model_dump()
        )
        db.add(ai_msg)
        await db.commit()
        await db.refresh(ai_msg)

        return ChatMessageResponse(
            id=ai_msg.id,
            project_id=ai_msg.project_id,
            user_id=ai_msg.user_id,
            task_id=ai_msg.task_id,
            sender=ai_msg.sender,
            message=ai_msg.message,
            context_used=context_summary,
            created_at=ai_msg.created_at
        )
