from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, portfolio, watchlist, market, alerts

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

app.include_router(health.router)
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
