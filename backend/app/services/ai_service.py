"""AI service wrapping the Anthropic Claude API.

Provides conversational chat about markets/portfolio and AI-driven asset analysis
that synthesizes technical indicators, market data, and reasoning.
"""

import logging

import anthropic

from app.config import settings
from app.services.store import store

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ORACLE, an AI investment intelligence assistant. Your role is to help investors make informed decisions by analyzing market data, technical indicators, and portfolio positions.

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


class AIService:
    """Handles all interactions with the Anthropic Claude API."""

    def __init__(self):
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured in .env")
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def chat(
        self,
        messages: list[dict],
        context: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Send a conversation to Claude and get a response.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            context: Additional context about portfolio/market data
            max_tokens: Max response length

        Returns:
            The assistant's text response.
        """
        client = self._get_client()

        system = SYSTEM_PROMPT

        # Inject AI memory for personalized context
        memories = store.get_memories(limit=20)
        if memories:
            memory_lines = []
            for m in memories:
                memory_lines.append(f"- [{m['category']}] {m['content']}")
            system += "\n\nYour memory (previous interactions and user preferences):\n" + "\n".join(memory_lines)

        if context:
            system += f"\n\nCurrent context:\n{context}"

        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )

        return response.content[0].text

    async def analyze_asset(
        self,
        symbol: str,
        technical_data: dict | None = None,
        quote_data: dict | None = None,
        portfolio_context: str = "",
    ) -> dict:
        """Generate AI analysis for an asset using available data.

        Args:
            symbol: Asset ticker symbol
            technical_data: Technical analysis indicators (RSI, MACD, etc.)
            quote_data: Current quote data (price, volume, change)
            portfolio_context: User's portfolio context if relevant

        Returns:
            Dict with: summary, signal, confidence, reasoning, risks, opportunities
        """
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
