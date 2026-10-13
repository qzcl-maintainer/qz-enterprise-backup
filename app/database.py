import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = os.environ.get("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/backup.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models  # noqa: F401 register models on Base before create_all

    Base.metadata.create_all(bind=engine)
    _migrate_jobs_table()


# create_all only creates missing tables — it never alters existing ones. These
# columns were added to `jobs` after the table already existed in the wild, so
# backfill them by hand for anyone upgrading an existing data/backup.db.
_JOBS_TABLE_ADDED_COLUMNS = {
    "source_location_id": "INTEGER REFERENCES storage_locations(id)",
    "destination_location_id": "INTEGER REFERENCES storage_locations(id)",
    "database_connection_id": "INTEGER REFERENCES database_connections(id)",
}


def _migrate_jobs_table() -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("jobs")}
    missing = {name: ddl for name, ddl in _JOBS_TABLE_ADDED_COLUMNS.items() if name not in existing}
    if not missing:
        return

    with engine.begin() as conn:
        for name, ddl in missing.items():
            conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}"))
