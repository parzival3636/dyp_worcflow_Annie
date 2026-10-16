import uuid
from collections.abc import Iterator
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

import backend.db as db_module
from backend.main import app
from backend.models import Project, Member, Task

# In-memory SQLite engine with StaticPool so all connections and threads share the same DB
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(autouse=True)
def clean_db():
    db_module.engine = test_engine
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def session() -> Iterator[Session]:
    with Session(test_engine) as sess:
        yield sess


import threading
_test_sqlite_lock = threading.RLock()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    # Ensure get_session uses test_engine with thread lock
    @contextmanager
    def test_get_session() -> Iterator[Session]:
        with _test_sqlite_lock:
            with Session(test_engine) as sess:
                yield sess

    orig_get_session = db_module.get_session
    db_module.get_session = test_get_session
    with TestClient(app) as test_client:
        yield test_client
    db_module.get_session = orig_get_session


@pytest.fixture
def sample_project(session: Session) -> Project:
    unique_code = f"TEST_{uuid.uuid4().hex[:6].upper()}"
    project = Project(
        code=unique_code,
        name="Test Project",
        status="running",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def sample_task(session: Session, sample_project: Project) -> Task:
    task = Task(
        project_id=sample_project.id,
        key="T-1",
        title="Sample Task 1",
        status="todo",
        progress=0,
        risk="ok",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
