import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import health, portfolio, watchlist, market, alerts, chat, ws, notifications

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ORACLE - AI Investment Intelligence Dashboard",
    description="AI-powered investment intelligence API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router)
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
