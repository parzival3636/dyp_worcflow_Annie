import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import repos, tasks, dashboard
from app.workers.webhook_worker import WebhookWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

worker = WebhookWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background webhook worker on app startup
    task = asyncio.create_task(worker.start())
    logger.info("Annie backend started")
    yield
    # Graceful shutdown
    worker.stop()
    task.cancel()
    logger.info("Annie backend shutting down")


app = FastAPI(
    title="Annie — GitHub Task Verification API",
    description="Automated task verification via GitHub commits + Gemini AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(repos.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "annie-backend"}
