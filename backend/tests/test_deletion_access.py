"""
test_deletion_access.py
-----------------------
Verifies that a mentor CANNOT see or act on deletion tickets that belong
to a different mentor.

Uses an isolated in-memory SQLite database so the live platform.db is untouched.
Requires: pytest, pytest-asyncio, httpx
  pip install pytest pytest-asyncio httpx

Run with:
  cd backend
  python -m pytest tests/test_deletion_access.py -v
"""
import uuid
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# ── App bootstrap ─────────────────────────────────────────────────────────────
# We monkey-patch the DATABASE_URL before the app is imported so SQLAlchemy
# uses an in-memory DB for the entire test session.
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.db.session import Base
from app.main import app
from app.api.deps import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.deletion_ticket import DeletionTicket

# ── In-memory test engine ─────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    """Create all tables once for the test module."""
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(scope="module")
async def seeded_data():
    """
    Create two mentors, one student assigned to mentor_a, one project
    linked to mentor_a, and a DeletionTicket assigned to mentor_a.
    Returns tokens for mentor_a and mentor_b.
    """
    mentor_a_id = str(uuid.uuid4())
    mentor_b_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    ticket_id = str(uuid.uuid4())

    async with TestSessionLocal() as db:
        mentor_a = User(
            id=mentor_a_id, email="mentor_a@test.com",
            hashed_password=get_password_hash("pw"),
            full_name="Mentor A", role=UserRole.MENTOR,
            mentor_code="MNT-AAAAA",
        )
        mentor_b = User(
            id=mentor_b_id, email="mentor_b@test.com",
            hashed_password=get_password_hash("pw"),
            full_name="Mentor B", role=UserRole.MENTOR,
            mentor_code="MNT-BBBBB",
        )
        student = User(
            id=student_id, email="student@test.com",
            hashed_password=get_password_hash("pw"),
            full_name="Student X", role=UserRole.STUDENT,
            assigned_mentor_id=mentor_a_id,
        )
        project = Project(
            id=project_id, title="Test Project",
            mentor_id=mentor_a_id, status="pending_deletion",
        )
        member = ProjectMember(
            id=str(uuid.uuid4()), project_id=project_id,
            user_id=student_id, role="OWNER",
        )
        ticket = DeletionTicket(
            id=ticket_id, project_id=project_id,
            student_id=student_id, mentor_id=mentor_a_id,
            reason="No longer needed", status="pending",
        )
        db.add_all([mentor_a, mentor_b, student, project, member, ticket])
        await db.commit()

    token_a = create_access_token(subject=mentor_a_id)
    token_b = create_access_token(subject=mentor_b_id)
    return {
        "ticket_id": ticket_id,
        "token_a": token_a,
        "token_b": token_b,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mentor_b_cannot_list_mentor_a_tickets(seeded_data):
    """Mentor B's ticket list must be empty — mentor A's ticket is invisible."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/deletion-tickets/",
            headers={"Authorization": f"Bearer {seeded_data['token_b']}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0, (
        f"Mentor B should see 0 tickets but got {len(data)}: {data}"
    )


@pytest.mark.asyncio
async def test_mentor_b_cannot_approve_mentor_a_ticket(seeded_data):
    """Mentor B attempting to approve mentor A's ticket must receive 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/deletion-tickets/{seeded_data['ticket_id']}/approve",
            headers={"Authorization": f"Bearer {seeded_data['token_b']}"},
        )
    assert resp.status_code == 404, (
        f"Expected 404 but got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_mentor_b_cannot_reject_mentor_a_ticket(seeded_data):
    """Mentor B attempting to reject mentor A's ticket must receive 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/deletion-tickets/{seeded_data['ticket_id']}/reject",
            headers={"Authorization": f"Bearer {seeded_data['token_b']}"},
            json={"rejection_note": "I am not your mentor"},
        )
    assert resp.status_code == 404, (
        f"Expected 404 but got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_mentor_a_can_list_own_tickets(seeded_data):
    """Mentor A must see exactly 1 pending ticket (their own)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/deletion-tickets/",
            headers={"Authorization": f"Bearer {seeded_data['token_a']}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == seeded_data["ticket_id"]


@pytest.mark.asyncio
async def test_mentor_a_can_reject_own_ticket(seeded_data):
    """Mentor A can reject their own ticket, rejection_note is stored."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/deletion-tickets/{seeded_data['ticket_id']}/reject",
            headers={"Authorization": f"Bearer {seeded_data['token_a']}"},
            json={"rejection_note": "Project still in use"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_note"] == "Project still in use"
