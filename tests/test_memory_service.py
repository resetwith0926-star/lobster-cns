from __future__ import annotations

from sqlalchemy import func, select

from app.models.memory import Memory
from app.services.memory_service import (
    CORE_MEMORY_SEED_RECORDS,
    CORE_MEMORY_SEED_SOURCE,
    MemoryService,
)


def test_create_memory_manually(db_session):
    service = MemoryService(db_session)

    memory = service.create_memory(
        namespace="brand",
        category="preference",
        content="ResetWith tone should be warm and practical.",
        importance=3,
    )

    assert memory.id is not None
    assert memory.namespace == "brand"


def test_retrieve_relevant_memory(db_session):
    service = MemoryService(db_session)
    service.create_memory(
        namespace="content",
        category="strategy",
        content="CNFCD content should explain metabolism simply.",
        importance=4,
    )

    memories = service.retrieve_relevant("metabolism CNFCD")

    assert len(memories) == 1
    assert "metabolism" in memories[0].content


def test_seed_core_memories_exist(db_session):
    service = MemoryService(db_session)

    created = service.seed_core_memories()

    assert created == len(CORE_MEMORY_SEED_RECORDS)
    rows = list(
        db_session.scalars(
            select(Memory).where(Memory.source == CORE_MEMORY_SEED_SOURCE)
        )
    )
    assert len(rows) == len(CORE_MEMORY_SEED_RECORDS)
    contents = {row.content for row in rows}
    for record in CORE_MEMORY_SEED_RECORDS:
        assert record["content"] in contents


def test_seed_core_memories_idempotent(db_session):
    service = MemoryService(db_session)

    first_created = service.seed_core_memories()
    second_created = service.seed_core_memories()

    assert first_created == len(CORE_MEMORY_SEED_RECORDS)
    assert second_created == 0
    count = db_session.scalar(
        select(func.count(Memory.id)).where(Memory.source == CORE_MEMORY_SEED_SOURCE)
    )
    assert count == len(CORE_MEMORY_SEED_RECORDS)
