import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin import router as admin_router
from api.config import router as config_router
from api.exploits import router as exploits_router
from api.flags import router as flags_router
from api.stats import router as stats_router
from api.teams import router as teams_router
from api.ws import router as ws_router
from config_manager import seed_defaults
from database import AsyncSessionLocal
from worker.scheduler import run_scheduler
from worker.submitter import run_submitter

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_defaults(db)

    submitter_task = asyncio.create_task(run_submitter(), name="submitter")
    scheduler_task = asyncio.create_task(run_scheduler(), name="scheduler")
    log.info("Background workers started (submitter + scheduler)")

    try:
        yield
    finally:
        scheduler_task.cancel()
        submitter_task.cancel()
        await asyncio.gather(scheduler_task, submitter_task, return_exceptions=True)
        log.info("Background workers stopped")


app = FastAPI(
    title="FarmRaid",
    description="CTF Attack & Defense Exploit Farm",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(teams_router, prefix="/api")
app.include_router(exploits_router, prefix="/api")
app.include_router(flags_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
