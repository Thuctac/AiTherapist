"""Bootstrap script that waits for Postgres, enables pgcrypto and creates tables."""

import os
import time
from typing import Optional

from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.exc import OperationalError

from models import Base  # make sure PYTHONPATH contains project root

DATABASE_URL="postgresql+psycopg2://chat_user:chat_pass@db:5432/chat_db"

# ---------------------------------------------------------------- helpers

def _pgcrypto_enable(connection):
    connection.execute(sql_text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))


def get_engine(url: Optional[str] = None):
    db_url = url or os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable must be set")

    echo_sql = bool(int(os.getenv("SQL_ECHO", "0")))
    return create_engine(db_url, echo=echo_sql, future=True)


# ---------------------------------------------------------------- main entry

def init_db(url: Optional[str] = None) -> None:
    """Wait until Postgres is ready and create schema."""

    engine = get_engine(url)

    # Wait (max 10 × 2 s) for the database to accept connections
    for _ in range(10):
        try:
            with engine.connect() as conn:
                conn.execute(sql_text("SELECT 1"))
            break
        except OperationalError:
            print("[init_db] waiting for database …")
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to the database after 10 tries")

    with engine.begin() as conn:
        _pgcrypto_enable(conn)
        Base.metadata.create_all(conn)

    print("✅ Database initialised & all tables created!")


if __name__ == "__main__":
    init_db(DATABASE_URL)
