"""AI service wrapping the Cerebras AI API (OpenAI-compatible).

Provides conversational chat about markets/portfolio and AI-driven asset analysis
that synthesizes technical indicators, market data, and reasoning.

Model strategy:
- llama-3.3-70b: Chat, asset analysis, decision synthesis (complex reasoning)
- llama3.1-8b: Sentiment analysis (classification, faster/cheaper)
"""

import logging

from openai import AsyncOpenAI

from app.config import settings
from app.services.store import store

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are InvestIA, an AI investment intelligence assistant. Your role is to help investors make informed decisions by analyzing market data, technical indicators, and portfolio positions.

Key guidelines:
- You do NOT provide financial advice. You provide decision support and analysis.
- Always explain your reasoning clearly and transparently.
- When discussing signals, explain what each indicator means and why it matters.
- Present information in a balanced way - cover both bullish and bearish perspectives.
- Use plain language but include technical details when relevant.
- If you don't have enough data, say so honestly.
- Never make promises about future performance.
- Include confidence levels when making assessments.

You have access to real-time market data, technical analysis (RSI, MACD, SMA, EMA, Bollinger Bands), portfolio holdings, and watchlists. When the user asks about specific assets, use the context provided to give informed analysis."""

# Model selection per task type
MODEL_CHAT = "llama-3.3-70b"       # Complex reasoning, multi-turn conversation
MODEL_ANALYSIS = "llama-3.3-70b"   # Asset analysis, decision synthesis
MODEL_SENTIMENT = "llama3.1-8b"    # Sentiment classification (faster/cheaper)

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"


class AIService:
    """Handles all interactions with the Cerebras AI API."""

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if not settings.cerebras_api_key:
            raise ValueError("CEREBRAS_API_KEY not configured in .env")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.cerebras_api_key,
                base_url=CEREBRAS_BASE_URL,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(settings.cerebras_api_key)

    async def chat(
        self,
        messages: list[dict],
        context: str = "",
        max_tokens: int = 1024,
        model: str | None = None,
        system_override: str | None = None,
        user_id: str = "",
    ) -> str:
        """Send a conversation to Cerebras and get a response.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            context: Additional context about portfolio/market data
            max_tokens: Max response length
            model: Override model (defaults to MODEL_CHAT)
            user_id: User ID for loading personalized memories

        Returns:
            The assistant's text response.
        """
        client = self._get_client()

        system = system_override or SYSTEM_PROMPT

        # Inject AI memory for personalized context
        memories = store.get_memories(user_id, limit=20) if user_id else []
        if memories:
            memory_lines = []
            for m in memories:
                memory_lines.append(f"- [{m['category']}] {m['content']}")
            system += "\n\nYour memory (previous interactions and user preferences):\n" + "\n".join(memory_lines)

        if context:
            system += f"\n\nCurrent context:\n{context}"

        # Build messages with system prompt as first message
        full_messages = [{"role": "system", "content": system}] + messages

        # Use the requested model, defaulting to MODEL_CHAT
        selected_model = model or MODEL_CHAT

        response = await client.chat.completions.create(
            model=selected_model,
            max_tokens=max_tokens,
            messages=full_messages,
        )

        return response.choices[0].message.content

    async def analyze_asset(
        self,
        symbol: str,
        technical_data: dict | None = None,
        quote_data: dict | None = None,
        portfolio_context: str = "",
    ) -> dict:
        """Generate AI analysis for an asset using available data."""
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

        if portfolio_context:
            context_parts.append(f"Portfolio context: {portfolio_context}")

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

        response_text = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            context=context,
            max_tokens=800,
            model=MODEL_ANALYSIS,
        )

        # Parse the signal from the overall technical data if available
        signal = "neutral"
        confidence = 0.5
        if technical_data:
            signal = technical_data.get("overall_signal", "neutral")
            counts = technical_data.get("signal_counts", {})
            total = sum(counts.values()) if counts else 1
            dominant = max(counts.values()) if counts else 0
            confidence = round(dominant / total, 2) if total > 0 else 0.5

        return {
            "symbol": symbol,
            "summary": response_text,
            "signal": signal,
            "confidence": confidence,
        }


# Singleton
ai_service = AIService()
