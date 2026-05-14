from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.services.event_log import EventLog


CORE_MEMORY_SEED_SOURCE = "system_seed_v0.1.2"
CORE_MEMORY_SEED_RECORDS = [
    {
        "namespace": "business",
        "category": "strategy",
        "importance": 5,
        "content": "ResetWith/CNFCD is the main business context. Lobster CNS exists to help operate, plan, and scale this business through AI agents.",
    },
    {
        "namespace": "brand",
        "category": "rule",
        "importance": 5,
        "content": "Premium Advisor CEO Brain tone should be warm, scientific, direct, practical, trust-building, and conversion-aware. It must not sound cold, robotic, exaggerated, or medically diagnostic.",
    },
    {
        "namespace": "system",
        "category": "rule",
        "importance": 5,
        "content": "v0.1.2 is CEO Governance Core only. CEOAgent may recommend and plan, but cannot publish, message, comment, browse, scrape, or execute external actions.",
    },
    {
        "namespace": "system",
        "category": "rule",
        "importance": 5,
        "content": "All external actions require human approval. simulation_only must always be true. requires_human_approval must always be true.",
    },
    {
        "namespace": "content",
        "category": "strategy",
        "importance": 4,
        "content": "Use Message Clarity and Behavior Change lenses to create educational posts, short video scripts, captions, email drafts, and brand content with clear transformation and small actionable steps.",
    },
    {
        "namespace": "sales",
        "category": "strategy",
        "importance": 4,
        "content": "Use Premium Advisor and Offer Architect lenses to detect buying intent, suggest soft CTAs, recommend follow-up actions, and never pressure users aggressively.",
    },
    {
        "namespace": "development",
        "category": "strategy",
        "importance": 4,
        "content": "Future Dev Agent should convert system needs into Codex-ready engineering tasks, bug reports, and implementation plans while preserving governance and safety constraints.",
    },
    {
        "namespace": "system",
        "category": "rule",
        "importance": 5,
        "content": "CEOAgent identity is Premium Advisor CEO Brain. It must not imitate the owner, impersonate real people, or claim biography-style identity.",
    },
    {
        "namespace": "system",
        "category": "strategy",
        "importance": 4,
        "content": "For every task, evaluate objective, target audience, business value, trust or objection issue, simplest message, next best action, required approvals, suitable future role, and success criteria.",
    },
]


class MemoryService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventLog(db)

    def create_memory(
        self,
        namespace: str,
        category: str,
        content: str,
        importance: int = 1,
        source: str = "manual",
        task_id: Optional[int] = None,
        actor: str = "admin",
    ) -> Memory:
        memory = Memory(
            namespace=namespace,
            category=category,
            content=content,
            importance=importance,
            source=source,
            task_id=task_id,
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        self.events.log(
            "memory_created",
            actor=actor,
            task_id=task_id,
            message=f"Memory created in {namespace}/{category}.",
            metadata={"memory_id": memory.id, "importance": importance},
        )
        return memory

    def seed_core_memories(self) -> int:
        existing_contents = set(
            self.db.scalars(
                select(Memory.content).where(Memory.source == CORE_MEMORY_SEED_SOURCE)
            )
        )
        created = 0
        for record in CORE_MEMORY_SEED_RECORDS:
            if record["content"] in existing_contents:
                continue
            self.create_memory(
                namespace=record["namespace"],
                category=record["category"],
                content=record["content"],
                importance=record["importance"],
                source=CORE_MEMORY_SEED_SOURCE,
                actor="system",
            )
            created += 1
        return created

    def get_memory(self, memory_id: int) -> Optional[Memory]:
        return self.db.get(Memory, memory_id)

    def list_memories(self, limit: int = 100):
        stmt = (
            select(Memory)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def retrieve_relevant(
        self,
        query: str,
        limit: int = 8,
        task_id: Optional[int] = None,
        actor: str = "ceo_agent",
    ):
        memories = self.list_memories(limit=200)
        query_words = self._keywords(query)

        scored = []
        for memory in memories:
            score = memory.importance
            memory_words = self._keywords(memory.content)
            score += len(query_words.intersection(memory_words)) * 2
            scored.append((score, memory.created_at, memory))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [memory for _, _, memory in scored[:limit]]
        self.events.log(
            "memory_retrieved",
            actor=actor,
            task_id=task_id,
            message=f"Retrieved {len(selected)} relevant memories.",
            metadata={"memory_ids": [memory.id for memory in selected]},
        )
        return selected

    def _keywords(self, text: str) -> Set[str]:
        separators = "\n\t,.;:!?()[]{}，。！？、"
        cleaned = text.lower()
        for char in separators:
            cleaned = cleaned.replace(char, " ")
        return {word for word in cleaned.split(" ") if len(word.strip()) >= 2}
