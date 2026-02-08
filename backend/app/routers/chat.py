from fastapi import APIRouter, HTTPException

from app.schemas.asset import (
    AIAnalysisResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.ai_service import ai_service
from app.services.market_data import market_data_service
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/status")
async def get_ai_status():
    """Check if AI service is configured and ready."""
    return {
        "configured": ai_service.is_configured,
        "model": "claude-sonnet-4-5-20250929",
    }


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the AI assistant and get a response.

    Supports multi-turn conversations via the messages array.
    Optionally include context about current portfolio/market state.
    """
    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set ANTHROPIC_API_KEY in .env",
        )

    try:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        response_text = await ai_service.chat(
            messages=messages,
            context=req.context,
        )

        # Auto-save last user message as interaction memory
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), None,
        )
        if last_user:
            store.save_memory(
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
async def analyze_asset(symbol: str):
    """Get AI-powered analysis for an asset.

    Fetches real-time quote and technical indicators, then asks Claude
    to synthesize them into an actionable analysis.
    """
    if not ai_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set ANTHROPIC_API_KEY in .env",
        )

    symbol = symbol.upper()

    # Gather market data
    quote = await market_data_service.get_quote(symbol)
    quote_data = quote if quote else None

    # Gather technical analysis
    technical_data = None
    history = market_data_service.get_history(symbol, period="6mo", interval="1d")
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
