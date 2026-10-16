import threading
from collections.abc import Iterator
from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine
from backend.config import settings

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}
_sqlite_lock = threading.RLock()

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 5

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)


def create_db_and_tables(target_engine=None):
    use_engine = target_engine or engine
    SQLModel.metadata.create_all(use_engine)


@contextmanager
def get_session() -> Iterator[Session]:
    if settings.DATABASE_URL.startswith("sqlite"):
        with _sqlite_lock:
            with Session(engine) as session:
                yield session
    else:
        with Session(engine) as session:
            yield session
