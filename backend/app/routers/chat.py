import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import AuthUser, get_current_user
from app.schemas.ai_explanation import StructuredAIAnalysisResponse
from app.schemas.asset import (
    ChatRequest,
    ChatResponse,
)
from app.services.ai_explanation_layer import explain_asset_analysis
from app.services.market_data import market_data_service
from app.services.news_service import news_service
from app.services.personas import get_all_personas, get_persona_prompt
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators
from app.services.inbox_service import (
    build_briefing_from_inbox,
    build_recommendations_from_inbox,
)
from app.services.prediction_service import generate_prediction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/status")
async def get_ai_status(user: AuthUser = Depends(get_current_user)):
    """Check if AI service is configured and ready."""
    from app.services.groq_service import groq_service

    return {
        "configured": groq_service.is_available(),
        "model": "groq-llama-3.1-70b-versatile",
    }


@router.post("/")
async def chat(req: ChatRequest, user: AuthUser = Depends(get_current_user)):
    """Send a message to the AI assistant and stream the response as SSE."""
    from app.services.groq_service import groq_service

    if not groq_service.is_available():
        raise HTTPException(status_code=503, detail="AI service is not configured")

    # Build portfolio/watchlist context for the user
    holdings = store.get_holdings(user.id, user.tenant_id)
    watchlists = store.get_watchlists(user.id, user.tenant_id)
    watchlist_symbols = []
    for wl in watchlists:
        watchlist_symbols.extend([a["symbol"] for a in wl.get("assets", [])])

    context_parts = []
    if holdings:
        lines = ["Portfolio actual del usuario:"]
        for h in holdings:
            sym = h["symbol"]
            qty = h.get("quantity", 0)
            avg = h.get("avg_buy_price", 0)
            lines.append(
                f"  - {sym}: {qty} acciones/unidades, precio medio de compra ${avg:.2f}"
            )
        context_parts.append("\n".join(lines))
    else:
        context_parts.append(
            "Portfolio: vacío (el usuario no tiene posiciones abiertas)."
        )

    if watchlist_symbols:
        context_parts.append(f"Watchlist del usuario: {', '.join(watchlist_symbols)}")

    system_prompt = f"""Eres InvestIA, una capa de explicacion para analisis de inversion. Tu rol es ayudar al usuario a entender datos estructurados, riesgos y escenarios, no improvisar recomendaciones magicas.

{chr(10).join(context_parts)}

Directrices de comportamiento:
- Responde siempre en el idioma del usuario.
- Primero explica hechos, senales y riesgos; luego resume escenarios.
- No inventes datos que no aparezcan en el contexto.
- Si faltan datos, dilo de forma explicita.
- No te presentes como autoridad final ni como asesor financiero regulado.
- Cuando haya senales contradictorias, exponlas claramente.
- Si el usuario pregunta que comprar o vender, responde en formato de decision support:
  * explica que informacion estructurada favorece o perjudica cada opcion
  * senala incertidumbre, concentration risk y horizonte temporal
  * evita imperativos tajantes
- SIEMPRE responde en el idioma que use el usuario. Si escribe en español, responde en español.
- Usa markdown solo cuando aporte claridad.
- Nunca hagas promesas de rentabilidad ni des garantias de resultados.
- Cierra con una nota breve indicando que el contenido es informativo y no constituye asesoramiento financiero."""

    all_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": m.role, "content": m.content} for m in req.messages
    ]

    async def generate():
        try:
            stream = await groq_service.stream_chat(
                messages=all_messages,
                model="powerful",
                temperature=0.7,
                max_tokens=1500,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/analyze/{symbol}", response_model=StructuredAIAnalysisResponse)
async def analyze_asset(symbol: str, user: AuthUser = Depends(get_current_user)):
    try:
        result = await explain_asset_analysis(
            symbol.upper(),
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        return StructuredAIAnalysisResponse(**result)
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")


@router.get("/personas")
async def list_personas(user: AuthUser = Depends(get_current_user)):
    """List available AI investor personas."""
    return {"personas": get_all_personas()}


@router.post("/persona-analyze")
async def persona_analyze(req: dict, user: AuthUser = Depends(get_current_user)):
    """Analyze a symbol from a specific persona's perspective."""
    from app.services.groq_service import groq_service

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

    context_parts = [f"Asset: {symbol}"]
    if quote_data:
        context_parts.append(
            f"Price: ${quote_data.get('price', 'N/A')}, "
            f"Change: {quote_data.get('change_percent', 'N/A')}%"
        )
    if technical_data:
        context_parts.append(
            f"Overall Technical Signal: {technical_data.get('overall_signal', 'N/A')}"
        )

    user_prompt = question or f"Analyze {symbol} and give your investment perspective."

    try:
        response = await groq_service.chat(
            prompt=user_prompt,
            model="powerful",
            system_prompt=persona_prompt + "\n\nContext:\n" + "\n".join(context_parts),
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
        return await build_briefing_from_inbox(user_id=user.id, tenant_id=user.tenant_id)
    except Exception as e:
        logger.error("Briefing generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Briefing generation error: {e}")


@router.get("/recommendations")
async def get_recommendations(user: AuthUser = Depends(get_current_user)):
    """Generate AI-powered investment recommendations from all data sources."""
    try:
        return await build_recommendations_from_inbox(
            user_id=user.id, tenant_id=user.tenant_id
        )
    except Exception as e:
        logger.error("Recommendations generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recommendations error: {e}")


@router.get("/news")
async def get_news(
    symbol: str | None = None, user: AuthUser = Depends(get_current_user)
):
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
