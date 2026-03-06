import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import AuthUser, get_current_user
from app.schemas.asset import (
    AIAnalysisResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.market_data import market_data_service
from app.services.news_service import news_service
from app.services.personas import get_all_personas, get_persona_prompt
from app.services.store import store
from app.services.technical_analysis import compute_all_indicators
from app.services.briefing_service import generate_briefing
from app.services.recommendations_service import generate_recommendations
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

    system_prompt = f"""Eres InvestIA, un asistente experto en análisis de inversiones. Tu rol es ayudar al usuario a tomar decisiones informadas sobre sus inversiones.

{chr(10).join(context_parts)}

Directrices de comportamiento:
- Eres un analista financiero experimentado, no un robot legal. Hablas con claridad y aportas valor real.
- SIEMPRE responde en el idioma que use el usuario. Si escribe en español, responde en español.
- Cuando el usuario pregunte qué comprar o en qué invertir, dale recomendaciones concretas y útiles:
  * Pregunta primero (si no lo sabes) sobre su perfil: horizonte temporal, tolerancia al riesgo, capital disponible.
  * Si ya tienes contexto suficiente, sugiere activos específicos con justificación: ETFs diversificados (VTI, SPY, QQQ), acciones líderes (AAPL, MSFT, NVDA), crypto (BTC, ETH) u otros según el perfil.
  * Estructura las sugerencias con pros, contras y nivel de riesgo.
- Si el portfolio está vacío, es una oportunidad para orientar sobre cómo empezar: diversificación, perfil de riesgo, horizonte temporal.
- Añade siempre un recordatorio breve de que el análisis es orientativo y no constituye asesoramiento financiero regulado.
- Cuando analices activos, usa datos técnicos (RSI, MACD, tendencias) si están disponibles en el contexto.
- Sé conciso pero completo. Usa markdown para estructurar respuestas largas.
- Nunca hagas promesas sobre rentabilidad futura ni des garantías de resultados."""

    all_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": m.role, "content": m.content} for m in req.messages
    ]

    async def generate():
        try:
            stream = await groq_service._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=all_messages,
                temperature=0.7,
                max_tokens=1500,
                stream=True,
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


@router.get("/analyze/{symbol}", response_model=AIAnalysisResponse)
async def analyze_asset(symbol: str, user: AuthUser = Depends(get_current_user)):
    """Get AI-powered analysis for an asset."""
    from app.services.groq_service import groq_service

    symbol = symbol.upper()

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
            f"Current Price: ${quote_data.get('price', 'N/A')}, "
            f"Change: {quote_data.get('change_percent', 'N/A')}%, "
            f"Volume: {quote_data.get('volume', 'N/A')}"
        )

    if technical_data:
        ta = technical_data
        rsi_val = ta.get("rsi", {}).get("value", "N/A")
        rsi_sig = ta.get("rsi", {}).get("signal", "N/A")
        macd_sig = ta.get("macd", {}).get("signal", "N/A")
        macd_hist = ta.get("macd", {}).get("histogram", "N/A")
        sma_sig = ta.get("sma", {}).get("signal", "N/A")
        ema_sig = ta.get("ema", {}).get("signal", "N/A")
        bb_sig = ta.get("bollinger_bands", {}).get("signal", "N/A")
        overall = ta.get("overall_signal", "N/A")
        counts = ta.get("signal_counts", {})

        context_parts.append(
            f"Technical Analysis:\n"
            f"- RSI: {rsi_val} ({rsi_sig})\n"
            f"- MACD histogram: {macd_hist} ({macd_sig})\n"
            f"- SMA signal: {sma_sig}\n"
            f"- EMA signal: {ema_sig}\n"
            f"- Bollinger Bands: {bb_sig}\n"
            f"- Overall: {overall} (Bullish: {counts.get('bullish', 0)}, "
            f"Bearish: {counts.get('bearish', 0)}, Neutral: {counts.get('neutral', 0)})"
        )

    context = "\n\n".join(context_parts)

    prompt = (
        f"Analyze {symbol} based on the data provided. Give a concise investment analysis with:\n"
        f"1. A one-sentence summary of the current situation\n"
        f"2. Your signal assessment (bullish, bearish, or neutral) with confidence (0-1)\n"
        f"3. Key reasoning points (2-3 bullets)\n"
        f"4. Top risks (1-2 bullets)\n"
        f"5. Potential opportunities (1-2 bullets)\n\n"
        f"Format your response as structured text with clear section headers."
    )

    system_prompt = """You are InvestIA, an AI investment intelligence assistant. Your role is to help investors make informed decisions by analyzing market data, technical indicators, and portfolio positions.

Key guidelines:
- You do NOT provide financial advice. You provide decision support and analysis.
- Always explain your reasoning clearly and transparently.
- When discussing signals, explain what each indicator means and why it matters.
- Present information in a balanced way - cover both bullish and bearish perspectives.
- Use plain language but include technical details when relevant.
- If you don't have enough data, say so honestly.
- Never make promises about future performance.
- Include confidence levels when making assessments."""

    try:
        response_text = await groq_service.chat(
            prompt=prompt,
            model="powerful",
            system_prompt=system_prompt + "\n\n" + context,
        )

        signal = "neutral"
        confidence = 0.5
        if technical_data:
            signal = technical_data.get("overall_signal", "neutral")
            counts = technical_data.get("signal_counts", {})
            total = sum(counts.values()) if counts else 1
            dominant = max(counts.values()) if counts else 0
            confidence = round(dominant / total, 2) if total > 0 else 0.5

        return AIAnalysisResponse(
            symbol=symbol,
            summary=response_text,
            signal=signal,
            confidence=confidence,
        )
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
