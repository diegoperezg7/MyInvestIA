"""Market-wide sentiment aggregation.

Computes a real sentiment index (-1 to +1) from multiple sources:
- Top stock performance (market breadth)
- VIX level
- Social/news sentiment if available
"""

import logging

logger = logging.getLogger(__name__)


async def compute_market_sentiment() -> float:
    """Compute an aggregated market sentiment index from -1.0 to +1.0."""
    scores: list[float] = []

    # 1. Market breadth signal (advance/decline)
    try:
        from app.services.sector_heatmap import get_market_breadth
        breadth = await get_market_breadth()
        adv = breadth.get("advancing", 0)
        dec = breadth.get("declining", 0)
        total = adv + dec
        if total > 0:
            ratio = (adv - dec) / total  # -1 to +1
            scores.append(ratio)
    except Exception as e:
        logger.debug("Breadth sentiment unavailable: %s", e)

    # 2. VIX-based fear (inverse: low VIX = bullish)
    try:
        from app.services.macro_intelligence import get_all_macro_indicators
        indicators = await get_all_macro_indicators()
        for ind in indicators:
            if ind.get("ticker") == "^VIX":
                vix = ind.get("value", 20)
                # VIX 10 → +0.8, VIX 20 → 0, VIX 35 → -1.0
                vix_score = max(-1.0, min(1.0, (20 - vix) / 15))
                scores.append(vix_score)
                break
    except Exception as e:
        logger.debug("VIX sentiment unavailable: %s", e)

    # 3. Sector performance average
    try:
        from app.services.sector_heatmap import get_sector_performance
        sectors = await get_sector_performance()
        perfs = [s.get("performance_1d", 0) for s in sectors.get("sectors", [])]
        if perfs:
            avg_perf = sum(perfs) / len(perfs)
            # Normalize: +2% → +0.6, -2% → -0.6
            perf_score = max(-1.0, min(1.0, avg_perf / 3.0))
            scores.append(perf_score)
    except Exception as e:
        logger.debug("Sector sentiment unavailable: %s", e)

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 3)
