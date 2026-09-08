from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base, AsyncSessionLocal
from sqlalchemy.future import select
from app.models.user import User
from app.api import auth, projects, tasks, planner, github, mentorship, mentor, chat, users, deletion_tickets, supervision

import app.models.user
import app.models.project
import app.models.task
import app.models.commit
import app.models.chat
import app.models.deletion_ticket
import app.models.supervisor_message

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe SQLite migrations for any columns added in new iterations
        try:
            await conn.exec_driver_sql("ALTER TABLE deletion_tickets ADD COLUMN rejection_note TEXT")
        except Exception:
            pass  # Already exists
        try:
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN mentor_code VARCHAR")
        except Exception:
            pass
        try:
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN assigned_mentor_id VARCHAR")
        except Exception:
            pass
        try:
            await conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'")
        except Exception:
            pass

    # Non-destructive backfill for legacy demo accounts
    async with AsyncSessionLocal() as db:
        try:
            mentor_res = await db.execute(select(User).where(User.email == "mentor@univ.edu"))
            demo_mentor = mentor_res.scalars().first()
            if demo_mentor and not demo_mentor.mentor_code:
                demo_mentor.mentor_code = "MNT-DEMO-01"
                await db.commit()
                await db.refresh(demo_mentor)

            if demo_mentor:
                student_res = await db.execute(select(User).where(User.email == "student@univ.edu"))
                demo_student = student_res.scalars().first()
                if demo_student and not demo_student.assigned_mentor_id:
                    demo_student.assigned_mentor_id = demo_mentor.id
                    await db.commit()
        except Exception as e:
            print(f"[STARTUP WARNING] Backfill legacy demo accounts skipped or encountered: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(planner.router, prefix=settings.API_V1_STR)
app.include_router(github.router, prefix=settings.API_V1_STR)
app.include_router(mentorship.router, prefix=settings.API_V1_STR)
app.include_router(mentor.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(deletion_tickets.router, prefix=settings.API_V1_STR)
app.include_router(supervision.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "status": "online",
        "docs": "/docs"
    }

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
