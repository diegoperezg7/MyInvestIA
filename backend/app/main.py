import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    health,
    portfolio,
    watchlist,
    market,
    alerts,
    chat,
    ws,
    notifications,
    memory,
)
from app.routers import (
    screener,
    transactions,
    paper_trading,
    openclaw,
    news,
    connections,
)
from app.routers import agents, user_profile, auth
from app.routers import rl_trading

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


async def _warmup_movers_cache():
    """Pre-warm the movers cache for US region in background on startup."""
    try:
        from app.routers.market import get_movers

        await get_movers(region="us", threshold=1.0)
        logger.info("Movers cache warmed up (US)")
    except Exception as e:
        logger.warning("Movers cache warmup failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm caches in background (don't block server start)
    asyncio.create_task(_warmup_movers_cache())

    # Start agent scheduler (runs every 30 min)
    from app.services.agent_orchestrator import orchestrator

    orchestrator.start_scheduler(interval_minutes=30)

    yield

    # Shutdown: stop agent scheduler
    orchestrator.stop_scheduler()


app = FastAPI(
    title="MyInvestIA - AI Investment Intelligence Dashboard",
    description="AI-powered investment intelligence API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(paper_trading.router, prefix="/api/v1")
app.include_router(openclaw.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(user_profile.router, prefix="/api/v1")
app.include_router(rl_trading.router, prefix="/api/v1")
