"""CSV import/export service for portfolio data."""

import csv
import io
import logging

logger = logging.getLogger(__name__)


def export_portfolio_csv(holdings: list[dict]) -> str:
    """Export portfolio holdings to CSV string.

    Args:
        holdings: List of holding dicts with symbol, name, type, quantity, avg_buy_price, etc.

    Returns:
        CSV string
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["symbol", "name", "type", "quantity", "avg_buy_price", "current_value", "unrealized_pnl"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for h in holdings:
        asset = h.get("asset", {})
        writer.writerow({
            "symbol": asset.get("symbol", h.get("symbol", "")),
            "name": asset.get("name", h.get("name", "")),
            "type": asset.get("type", h.get("type", "stock")),
            "quantity": h.get("quantity", 0),
            "avg_buy_price": h.get("avg_buy_price", 0),
            "current_value": h.get("current_value", 0),
            "unrealized_pnl": h.get("unrealized_pnl", 0),
        })
    return output.getvalue()


def parse_portfolio_csv(csv_content: str) -> list[dict]:
    """Parse CSV content into portfolio holdings.

    Expected columns: symbol, quantity, avg_buy_price
    Optional: name, type

    Returns:
        List of holding dicts ready for import
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    holdings = []

    for row in reader:
        symbol = row.get("symbol", "").strip().upper()
        if not symbol:
            continue

        try:
            holding = {
                "symbol": symbol,
                "name": row.get("name", symbol),
                "type": row.get("type", "stock"),
                "quantity": float(row.get("quantity", 0)),
                "avg_buy_price": float(row.get("avg_buy_price", 0)),
            }
            if holding["quantity"] > 0 and holding["avg_buy_price"] > 0:
                holdings.append(holding)
        except (ValueError, TypeError) as e:
            logger.warning("Skipping invalid CSV row for %s: %s", symbol, e)
            continue

    return holdings
