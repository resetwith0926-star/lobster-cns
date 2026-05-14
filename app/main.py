from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import (
    agents,
    draft_reviews,
    drafts,
    dashboard,
    events,
    health,
    llm_calls,
    memory,
    system,
    tasks,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Lobster CNS",
    version="0.1.2",
    description="CEO Governance Core for ResetWith/CNFCD.",
    lifespan=lifespan,
)


app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(drafts.router)
app.include_router(draft_reviews.router)
app.include_router(agents.router)
app.include_router(events.router)
app.include_router(memory.router)
app.include_router(llm_calls.router)
app.include_router(system.router)
app.include_router(dashboard.router)
