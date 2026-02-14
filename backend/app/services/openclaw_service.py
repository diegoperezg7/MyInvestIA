"""OpenClaw integration service.

Connects to a self-hosted OpenClaw AI agent (Docker) for:
- Delivering alerts via Telegram (and other channels)
- Running agent tasks (portfolio analysis, market monitoring)
- Triggering heartbeat wake events

OpenClaw Gateway expected at OPENCLAW_URL (default http://localhost:18789).
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OpenClawService:
    """Client for the OpenClaw webhook API."""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.openclaw_enabled and settings.openclaw_token)

    @property
    def base_url(self) -> str:
        return settings.openclaw_url.rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.openclaw_token}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # --- Core webhook methods ---

    async def wake(self, text: str) -> dict | None:
        """Send a wake event to OpenClaw's main session.

        Use for simple notifications — OpenClaw processes the text
        and forwards to Telegram.
        """
        if not self.configured:
            logger.warning("OpenClaw not configured — skipping wake")
            return None

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/hooks/wake",
                headers=self._headers(),
                json={"text": text, "mode": "now"},
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
        except Exception as e:
            logger.warning("OpenClaw wake failed: %s", e)
            return None

    async def run_agent(
        self,
        message: str,
        name: str = "MyInvestIA Alert",
        session_key: str | None = None,
    ) -> dict | None:
        """Run an isolated agent task on OpenClaw.

        Use for complex tasks that need AI reasoning — portfolio analysis,
        market commentary, multi-step alert processing.
        """
        if not self.configured:
            logger.warning("OpenClaw not configured — skipping agent task")
            return None

        try:
            client = await self._get_client()
            payload: dict = {"message": message, "name": name}
            if session_key:
                payload["sessionKey"] = session_key

            resp = await client.post(
                f"{self.base_url}/hooks/agent",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "accepted"}
        except Exception as e:
            logger.warning("OpenClaw agent task failed: %s", e)
            return None

    # --- Alert delivery ---

    async def send_alert(self, alert: dict) -> dict | None:
        """Format and send an investment alert through OpenClaw.

        OpenClaw will process the alert with AI reasoning and deliver
        to Telegram (and any other configured channels).
        """
        severity = alert.get("severity", "low").upper()
        symbol = alert.get("asset_symbol", "N/A")
        title = alert.get("title", "Alert")
        description = alert.get("description", "")
        action = alert.get("suggested_action", "monitor").upper()
        confidence = alert.get("confidence", 0.0)
        reasoning = alert.get("reasoning", "")

        message = (
            f"MyInvestIA Investment Alert — Severity: {severity}\n\n"
            f"**{title}**\n"
            f"Symbol: {symbol}\n"
            f"{description}\n\n"
            f"Suggested action: {action} (confidence: {confidence:.0%})\n"
        )
        if reasoning:
            message += f"Reasoning: {reasoning}\n"

        message += (
            "\nPlease forward this alert to the user via Telegram. "
            "Add a brief AI commentary on whether this signal aligns "
            "with current market conditions."
        )

        return await self.run_agent(message, name=f"Alert: {symbol} {severity}")

    async def send_market_summary(self, summary_data: dict) -> dict | None:
        """Send a market overview summary through OpenClaw for AI commentary."""
        gainers = summary_data.get("gainers", [])
        losers = summary_data.get("losers", [])
        macro = summary_data.get("macro", [])

        parts = ["Generate a brief market summary and send it to the user via Telegram.\n"]

        if gainers:
            parts.append("Top Gainers:")
            for g in gainers[:5]:
                parts.append(f"  {g['symbol']}: {g['price']} ({g['change_percent']:+.2f}%)")

        if losers:
            parts.append("Top Losers:")
            for l in losers[:5]:
                parts.append(f"  {l['symbol']}: {l['price']} ({l['change_percent']:+.2f}%)")

        if macro:
            parts.append("Macro Indicators:")
            for m in macro:
                parts.append(f"  {m['name']}: {m['value']} ({m['trend']})")

        parts.append(
            "\nProvide a 2-3 sentence interpretation of these conditions "
            "and any actionable takeaways for the investor."
        )

        return await self.run_agent("\n".join(parts), name="Market Summary")

    async def send_portfolio_update(self, portfolio_data: dict) -> dict | None:
        """Send portfolio status through OpenClaw for AI commentary."""
        total = portfolio_data.get("total_value", 0)
        pnl = portfolio_data.get("daily_pnl", 0)
        pnl_pct = portfolio_data.get("daily_pnl_percent", 0)
        holdings = portfolio_data.get("holdings", [])

        parts = [
            "Send the user a portfolio status update via Telegram.\n",
            f"Total Value: ${total:,.2f}",
            f"Daily P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)\n",
            "Holdings:",
        ]

        for h in holdings[:10]:
            asset = h.get("asset", {})
            parts.append(
                f"  {asset.get('symbol', '?')}: "
                f"${h.get('current_value', 0):,.2f} "
                f"(PnL: ${h.get('unrealized_pnl', 0):,.2f})"
            )

        parts.append(
            "\nBriefly comment on the portfolio's risk exposure "
            "and any positions that warrant attention."
        )

        return await self.run_agent("\n".join(parts), name="Portfolio Update")

    async def query_portfolio(self, question: str) -> dict | None:
        """Let OpenClaw answer a question about the portfolio.

        This enables Telegram chat: user asks question in Telegram,
        OpenClaw calls MyInvestIA API, reasons over data, and replies.
        """
        message = (
            f"The user is asking about their portfolio: \"{question}\"\n\n"
            f"Use the MyInvestIA API at http://host.docker.internal:8000/api/v1 to look up:\n"
            f"- GET /portfolio/ for holdings and P&L\n"
            f"- GET /market/quote/{{symbol}} for current prices\n"
            f"- GET /market/analysis/{{symbol}} for technical analysis\n"
            f"- GET /market/sentiment/{{symbol}} for AI sentiment\n"
            f"- GET /alerts/scan for current alerts\n"
            f"- GET /market/macro for macro indicators\n\n"
            f"Answer the user's question based on the data. "
            f"Reply in the same language the user used."
        )

        return await self.run_agent(message, name="Portfolio Query")

    # --- Health check ---

    async def health_check(self) -> dict:
        """Check if OpenClaw is reachable."""
        if not settings.openclaw_enabled:
            return {"status": "disabled", "configured": False}

        if not settings.openclaw_token:
            return {"status": "not_configured", "configured": False}

        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.base_url}/",
                timeout=5.0,
            )
            return {
                "status": "connected" if resp.status_code < 500 else "error",
                "configured": True,
                "url": self.base_url,
                "http_status": resp.status_code,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "configured": True,
                "url": self.base_url,
                "error": str(e),
            }


# Singleton
openclaw_service = OpenClawService()
