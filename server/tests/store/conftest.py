"""Shared pieces for the store tests. Every test gets its own in-memory database."""

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Engine

from tacto.store.db import create_database


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_database("sqlite://")
    yield engine
    engine.dispose()
