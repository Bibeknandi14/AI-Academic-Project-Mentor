"""
test_mentor_linkage.py
----------------------
End-to-end integration tests verifying:
1. Student-mentor linkage propagates to all existing and newly created projects.
2. Supervision chat gating works seamlessly once linked.
3. Mentor's /supervision/students returns linked students with their projects and statistics.
4. Unlinking cleanly clears mentor_id across all projects.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.db.session import Base
from app.main import app as fastapi_app
from app.api.deps import get_db

import app.models.user
import app.models.project
import app.models.task
import app.models.commit
import app.models.chat
import app.models.deletion_ticket
import app.models.supervisor_message

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_linkage_propagation_and_supervision():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        # 1. Register Mentor
        mentor_reg = await client.post("/api/auth/register", json={
            "email": "faculty_turing@university.edu",
            "password": "Password123!",
            "full_name": "Dr. Alan Turing",
            "role": "MENTOR",
        })
        assert mentor_reg.status_code == 201, mentor_reg.text
        mentor_data = mentor_reg.json()
        mentor_code = mentor_data["mentor_code"]
        mentor_id = mentor_data["id"]
        assert mentor_code is not None

        mentor_token = (await client.post("/api/auth/login", data={
            "username": "faculty_turing@university.edu", "password": "Password123!"
        })).json()["access_token"]
        mentor_auth = {"Authorization": f"Bearer {mentor_token}"}

        # 2. Register Student independently (no mentor_code initially)
        student_reg = await client.post("/api/auth/register", json={
            "email": "student_ada@university.edu",
            "password": "Password123!",
            "full_name": "Ada Lovelace",
            "role": "STUDENT",
        })
        assert student_reg.status_code == 201, student_reg.text
        student_id = student_reg.json()["id"]

        student_token = (await client.post("/api/auth/login", data={
            "username": "student_ada@university.edu", "password": "Password123!"
        })).json()["access_token"]
        student_auth = {"Authorization": f"Bearer {student_token}"}

        # 3. Student creates project BEFORE linking mentor
        proj_create = await client.post("/api/projects/", json={
            "title": "Analytical Engine Simulation",
            "description": "Building computer architecture emulator",
            "github_repo": "ada/analytical-engine",
        }, headers=student_auth)
        assert proj_create.status_code == 201, proj_create.text
        project_1 = proj_create.json()
        assert project_1["mentor_id"] is None

        # 4. Student adds a task
        task_res = await client.post("/api/tasks/", json={
            "project_id": project_1["id"],
            "title": "Implement arithmetic logic circuits",
            "status": "DONE",
            "priority": "HIGH",
        }, headers=student_auth)
        assert task_res.status_code == 201

        # 5. Student links to mentor via /users/me/mentor
        link_res = await client.patch("/api/users/me/mentor", json={
            "mentor_code": mentor_code
        }, headers=student_auth)
        assert link_res.status_code == 200
        assert link_res.json()["assigned_mentor_id"] == mentor_id

        # 6. Verify existing project was automatically updated with mentor_id
        proj_fetch = await client.get(f"/api/projects/{project_1['id']}", headers=student_auth)
        assert proj_fetch.status_code == 200
        assert proj_fetch.json()["mentor_id"] == mentor_id

        # 7. Verify mentor can see student and project in /supervision/students
        students_res = await client.get("/api/supervision/students", headers=mentor_auth)
        assert students_res.status_code == 200
        students_list = students_res.json()
        assert len(students_list) == 1
        assert students_list[0]["id"] == student_id
        assert len(students_list[0]["projects"]) == 1
        p_summary = students_list[0]["projects"][0]
        assert p_summary["id"] == project_1["id"]
        assert p_summary["total_tasks"] == 1
        assert p_summary["completed_tasks"] == 1

        # 8. Verify Supervision Chat unlocks and messages can be sent bidirectionally
        # Student -> Mentor message
        send_std = await client.post(f"/api/supervision/messages/{project_1['id']}", json={
            "project_id": project_1["id"],
            "message": "Hello Professor Turing, I completed the logic circuits task!"
        }, headers=student_auth)
        assert send_std.status_code == 201
        assert send_std.json()["receiver_id"] == mentor_id

        # Mentor -> Student message
        send_mnt = await client.post(f"/api/supervision/messages/{project_1['id']}", json={
            "project_id": project_1["id"],
            "message": "Excellent work Ada. Proceed to memory store architecture."
        }, headers=mentor_auth)
        assert send_mnt.status_code == 201
        assert send_mnt.json()["receiver_id"] == student_id

        # Read messages from both sides
        msgs_std = await client.get(f"/api/supervision/messages/{project_1['id']}", headers=student_auth)
        assert msgs_std.status_code == 200
        assert len(msgs_std.json()) == 2

        msgs_mnt = await client.get(f"/api/supervision/messages/{project_1['id']}", headers=mentor_auth)
        assert msgs_mnt.status_code == 200
        assert len(msgs_mnt.json()) == 2

        # 9. Verify NEW project created by linked student automatically gets mentor_id
        proj2_create = await client.post("/api/projects/", json={
            "title": "Bernoulli Number Calculator",
            "description": "Algorithm for Bernoulli sequence generation",
        }, headers=student_auth)
        assert proj2_create.status_code == 201
        assert proj2_create.json()["mentor_id"] == mentor_id

        # 10. Test unlinking clears mentor_id
        unlink_res = await client.delete("/api/users/me/mentor", headers=student_auth)
        assert unlink_res.status_code == 200
        assert unlink_res.json()["assigned_mentor_id"] is None

        p1_after_unlink = (await client.get(f"/api/projects/{project_1['id']}", headers=student_auth)).json()
        assert p1_after_unlink["mentor_id"] is None
