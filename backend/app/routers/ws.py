"""WebSocket endpoint for real-time price streaming.

Clients connect and send a JSON message to subscribe:
  {"action": "subscribe", "symbols": ["AAPL", "BTC"], "interval": 5}

The server streams price updates at the requested interval (default 10s, min 5s).

Clients can update subscriptions at any time by sending another subscribe message.
Send {"action": "unsubscribe"} to stop receiving updates.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.market_data import market_data_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

MIN_INTERVAL = 5
DEFAULT_INTERVAL = 10
MAX_SYMBOLS = 20


async def _fetch_prices(symbols: list[str]) -> list[dict]:
    """Fetch current prices for a list of symbols."""
    results = []
    for sym in symbols[:MAX_SYMBOLS]:
        quote = await market_data_service.get_quote(sym)
        if quote:
            results.append({
                "symbol": quote["symbol"],
                "price": quote["price"],
                "change_percent": quote["change_percent"],
                "volume": quote.get("volume", 0),
            })
    return results


@router.websocket("/ws/prices")
async def price_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming price updates.

    Protocol:
    1. Client connects
    2. Client sends: {"action": "subscribe", "symbols": ["AAPL", "MSFT"], "interval": 10}
    3. Server streams: {"type": "prices", "data": [...], "timestamp": "..."}
    4. Client can send: {"action": "unsubscribe"} to pause
    5. Client can update subscription at any time
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    subscribed_symbols: list[str] = []
    interval: int = DEFAULT_INTERVAL
    streaming = False
    stream_task: asyncio.Task | None = None

    async def stream_prices():
        """Background task that sends price updates."""
        nonlocal streaming
        try:
            while streaming and subscribed_symbols:
                prices = await _fetch_prices(subscribed_symbols)
                await websocket.send_json({
                    "type": "prices",
                    "data": prices,
                })
                await asyncio.sleep(interval)
        except WebSocketDisconnect:
            streaming = False
        except Exception as e:
            logger.warning("Price stream error: %s", e)
            streaming = False

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action", "")

            if action == "subscribe":
                symbols = msg.get("symbols", [])
                if not isinstance(symbols, list) or not symbols:
                    await websocket.send_json({"type": "error", "message": "symbols must be a non-empty list"})
                    continue

                subscribed_symbols = [s.upper() for s in symbols[:MAX_SYMBOLS] if isinstance(s, str)]
                interval = max(MIN_INTERVAL, int(msg.get("interval", DEFAULT_INTERVAL)))

                # Stop existing stream
                if stream_task and not stream_task.done():
                    streaming = False
                    stream_task.cancel()
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass

                # Start new stream
                streaming = True
                stream_task = asyncio.create_task(stream_prices())

                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": subscribed_symbols,
                    "interval": interval,
                })

            elif action == "unsubscribe":
                streaming = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass
                subscribed_symbols = []
                await websocket.send_json({"type": "unsubscribed"})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        streaming = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
