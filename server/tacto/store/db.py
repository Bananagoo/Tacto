"""Open the database. One SQLite file, no server, so the product works with Wi-Fi off."""

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool
from sqlmodel import create_engine

from . import tables

# Relative to `server/`, where the server is started. `server/data/` is gitignored.
DEFAULT_DATABASE_URL = "sqlite:///data/tacto.db"

_IN_MEMORY = (None, "", ":memory:")


def create_database(url: str = DEFAULT_DATABASE_URL) -> Engine:
    """An engine for the database at `url`, with every table present.

    Safe to call on a database that already exists: tables are only created when missing,
    and nothing in them is touched.
    """
    engine = _create_engine(url)
    tables.metadata.create_all(engine)
    return engine


def _create_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return create_engine(url)
    if parsed.database in _IN_MEMORY:
        # An in-memory database belongs to one connection. Sharing that connection is the
        # only way requests handled on different threads see the same data.
        engine = create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    else:
        # SQLite creates the file but not the directory it sits in.
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url)
    event.listen(engine, "connect", _enforce_foreign_keys)
    return engine


def _enforce_foreign_keys(connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    # SQLite ignores foreign keys unless asked on every connection. With them on, a row
    # that points at a missing lesson or learner is an error and not a silent orphan.
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
