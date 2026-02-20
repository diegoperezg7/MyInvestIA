import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import AuthUser, get_current_user
from app.schemas.asset import (
    AIAnalysisResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.ai_service import ai_service
from app.services.analysis_pipeline import run_analysis_pipeline
from app.services.briefing_service import generate_briefing
from app.services.prediction_service import generate_prediction
from app.services.recommendations_service import generate_recommendations
from app.services.market_data import market_data_service
from app.services.news_service import news_service
from app.services.personas import get_all_personas, get_persona_prompt
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/status")
async def get_ai_status(user: AuthUser = Depends(get_current_user)):
    """Check if AI service is configured and ready."""
    return {
        "configured": ai_service.is_configured,
        "model": "mistral-large-latest",
    }


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, user: AuthUser = Depends(get_current_user)):
    """Send a message to the AI assistant and get a response."""
    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set MISTRAL_API_KEY in .env",
        )

    try:
        # Enrich context with portfolio risk & user profile
        enriched_context = req.context
        try:
            context_parts = [req.context] if req.context else []

            # User profile
            from app.routers.user_profile import _load_profile
            profile = _load_profile(user.id)
            if profile.get("risk_tolerance"):
                context_parts.append(
                    f"User profile: risk_tolerance={profile['risk_tolerance']}, "
                    f"horizon={profile.get('investment_horizon', 'medium')}, "
                    f"goals={', '.join(profile.get('goals', [])) or 'not set'}"
                )

            # Portfolio risk snapshot
            holdings = store.get_holdings(user.id)
            if holdings:
                from app.services.portfolio_risk import calculate_portfolio_risk
                enriched = []
                for h in holdings[:10]:  # limit to avoid slow context
                    q = await market_data_service.get_quote(h["symbol"], h.get("type"))
                    p = q.get("price", h["avg_buy_price"]) if q else h["avg_buy_price"]
                    enriched.append({**h, "current_price": p, "current_value": p * h["quantity"]})
                risk = await calculate_portfolio_risk(enriched)
                m = risk.get("metrics", {})
                context_parts.append(
                    f"Portfolio risk: VaR95={m.get('var_95', 0):.0f}, "
                    f"Sharpe={m.get('sharpe_ratio', 0):.2f}, "
                    f"Beta={m.get('beta', 0):.2f}, "
                    f"MaxDD={m.get('max_drawdown', 0):.1%}, "
                    f"Volatility={m.get('annual_volatility', 0):.1%}"
                )

            # Recent alerts
            recent_alerts = store.get_memories(user.id, category="alert_history", limit=5)
            if recent_alerts:
                alert_lines = [f"- {a['content']} ({a.get('metadata', {}).get('severity', '?')})" for a in recent_alerts]
                context_parts.append("Recent alerts:\n" + "\n".join(alert_lines))

            enriched_context = "\n\n".join(context_parts)
        except Exception as ctx_err:
            logger.debug("Context enrichment partial failure: %s", ctx_err)

        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        response_text = await ai_service.chat(
            messages=messages,
            context=enriched_context,
            user_id=user.id,
        )

        # Auto-save last user message as interaction memory
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), None,
        )
        if last_user:
            store.save_memory(
                user_id=user.id,
                category="interaction",
                content=last_user[:500],
                metadata={"response_preview": response_text[:200]},
            )

        return ChatResponse(response=response_text)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {e}")


@router.get("/analyze/{symbol}", response_model=AIAnalysisResponse)
async def analyze_asset(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Get AI-powered analysis for an asset."""
    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set MISTRAL_API_KEY in .env",
        )

    symbol = symbol.upper()

    quote = await market_data_service.get_quote(symbol)
    quote_data = quote if quote else None

    technical_data = None
    history = await market_data_service.get_history(symbol, period="6mo", interval="1d")
    if history and len(history) >= 30:
        closes = [r["close"] for r in history]
        technical_data = compute_all_indicators(closes)

    try:
        result = await ai_service.analyze_asset(
            symbol=symbol,
            technical_data=technical_data,
            quote_data=quote_data,
        )
        return AIAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {e}")


@router.get("/personas")
async def list_personas(user: AuthUser = Depends(get_current_user)):
    """List available AI investor personas."""
    return {"personas": get_all_personas()}


@router.post("/persona-analyze")
async def persona_analyze(req: dict, user: AuthUser = Depends(get_current_user)):
    """Analyze a symbol from a specific persona's perspective."""
    symbol = req.get("symbol", "").upper()
    persona_id = req.get("persona_id", "buffett")
    question = req.get("question", "")

    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    persona_prompt = get_persona_prompt(persona_id)
    if not persona_prompt:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    quote = await market_data_service.get_quote(symbol)
    quote_data = quote if quote else None

    technical_data = None
    history = await market_data_service.get_history(symbol, period="6mo", interval="1d")
    if history and len(history) >= 30:
        closes = [r["close"] for r in history]
        technical_data = compute_all_indicators(closes)

    if not ai_service.is_configured:
        raise HTTPException(status_code=503, detail="AI service not configured")

    context_parts = [f"Asset: {symbol}"]
    if quote_data:
        context_parts.append(
            f"Price: ${quote_data.get('price', 'N/A')}, "
            f"Change: {quote_data.get('change_percent', 'N/A')}%"
        )
    if technical_data:
        context_parts.append(f"Overall Technical Signal: {technical_data.get('overall_signal', 'N/A')}")

    user_prompt = question or f"Analyze {symbol} and give your investment perspective."

    try:
        response = await ai_service.chat(
            messages=[{"role": "user", "content": user_prompt}],
            context="\n".join(context_parts),
            system_override=persona_prompt,
            user_id=user.id,
        )
        return {
            "symbol": symbol,
            "persona_id": persona_id,
            "analysis": response,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona analysis error: {e}")


@router.get("/briefing")
async def get_briefing(user: AuthUser = Depends(get_current_user)):
    """Generate a proactive AI briefing from portfolio, watchlist, news, and macro data."""
    try:
        return await generate_briefing(user_id=user.id)
    except Exception as e:
        logger.error("Briefing generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Briefing generation error: {e}")


@router.get("/recommendations")
async def get_recommendations(user: AuthUser = Depends(get_current_user)):
    """Generate AI-powered investment recommendations from all data sources."""
    try:
        return await generate_recommendations(user_id=user.id)
    except Exception as e:
        logger.error("Recommendations generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recommendations error: {e}")


@router.get("/news")
async def get_news(symbol: str | None = None, user: AuthUser = Depends(get_current_user)):
    """Get market or company-specific news from Finnhub."""
    if not news_service.is_configured:
        return {"articles": [], "source": "finnhub", "configured": False}

    try:
        if symbol:
            articles = await news_service.get_company_news(symbol.upper())
        else:
            articles = await news_service.get_market_news()
        return {"articles": articles, "source": "finnhub", "configured": True}
    except Exception as e:
        logger.error("News fetch failed: %s", e)
        raise HTTPException(status_code=500, detail=f"News fetch error: {e}")


@router.get("/predict/{symbol}")
async def predict_symbol(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Generate an all-in-one prediction for a symbol."""
    try:
        return await generate_prediction(user_id=user.id, symbol=symbol)
    except Exception as e:
        logger.error("Prediction generation failed for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")


@router.get("/analyze-pipeline/{symbol}")
async def analyze_pipeline(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Run multi-step analysis pipeline with SSE progress streaming."""
    return StreamingResponse(
        run_analysis_pipeline(symbol),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
