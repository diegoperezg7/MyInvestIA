import time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AuthUser, get_current_user

from app.schemas.asset import (
    Asset,
    AssetQuote,
    AssetType,
    BollingerBandsIndicator,
    FilingsResponse,
    EMAIndicator,
    EconomicCalendarResponse,
    FundamentalsResponse,
    HistoricalData,
    HistoricalDataPoint,
    InsiderActivityResponse,
    MACDIndicator,
    MacroIndicator,
    MacroIndicatorDetail,
    MacroIntelligenceResponse,
    MacroSummary,
    MarketBreadthIndicators,
    MarketOverview,
    RSIIndicator,
    SMAIndicator,
    SectorHeatmapResponse,
    SentimentAnalysisResponse,
    TechnicalAnalysis,
)
from app.schemas.scoring import AssetScoreResponse
from app.services.scoring_engine import build_asset_score
from app.schemas.signals import SignalSummary
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import COMMODITY_FUTURES_MAP, market_data_service
from app.services.macro_context_service import get_macro_context
from app.services.news_aggregator import get_ai_analyzed_feed
from app.services.news_intelligence import build_social_sentiment_from_articles
from app.services.news_service import news_service
from app.services.provider_chain import provider_chain
from app.services.sentiment_service import analyze_sentiment
from app.services.signal_aggregator import build_signal_summary
from app.services.technical_analysis import compute_all_indicators
from app.services.volatility_service import compute_volatility

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(get_current_user)])

# Endpoint-level cache for movers (avoids re-fetching 400+ symbols on every request)
_movers_cache: dict[str, tuple[float, dict]] = {}
_MOVERS_CACHE_TTL = 180  # 3 minutes


@router.get("/", response_model=MarketOverview)
async def get_market_overview():
    """Get market overview with top movers from major stocks."""
    from app.services.sentiment_aggregator import compute_market_sentiment

    movers = await market_data_service.get_top_movers()

    gainers = [
        Asset(
            symbol=q["symbol"],
            name=q["name"],
            type=AssetType.STOCK,
            price=q["price"],
            change_percent=q["change_percent"],
            volume=q["volume"],
        )
        for q in movers.get("gainers", [])
    ]
    losers = [
        Asset(
            symbol=q["symbol"],
            name=q["name"],
            type=AssetType.STOCK,
            price=q["price"],
            change_percent=q["change_percent"],
            volume=q["volume"],
        )
        for q in movers.get("losers", [])
    ]

    # Fetch macro indicators and sentiment in parallel
    import asyncio
    macro_task = get_all_macro_indicators()
    sentiment_task = compute_market_sentiment()
    macro_raw, sentiment_index = await asyncio.gather(macro_task, sentiment_task)

    macro_indicators = [
        MacroIndicator(
            name=m["name"],
            value=m["value"],
            trend=m["trend"],
            impact_description=m["impact_description"],
        )
        for m in macro_raw
    ]

    return MarketOverview(
        sentiment_index=sentiment_index,
        top_gainers=gainers,
        top_losers=losers,
        macro_indicators=macro_indicators,
    )


@router.get("/providers")
async def get_providers():
    """Get status of all configured market data providers."""
    return {"providers": provider_chain.providers}


# ── Symbol search catalog ──
# Comprehensive catalog for autocomplete: (symbol, name, type)
_SYMBOL_CATALOG: list[tuple[str, str, str]] = [
    # US Mega-cap
    ("AAPL", "Apple Inc.", "stock"), ("MSFT", "Microsoft Corp.", "stock"),
    ("GOOGL", "Alphabet (Google)", "stock"), ("GOOG", "Alphabet Class C", "stock"),
    ("AMZN", "Amazon.com Inc.", "stock"), ("NVDA", "NVIDIA Corp.", "stock"),
    ("META", "Meta Platforms", "stock"), ("TSLA", "Tesla Inc.", "stock"),
    ("AVGO", "Broadcom Inc.", "stock"), ("ORCL", "Oracle Corp.", "stock"),
    # Semiconductors
    ("AMD", "Advanced Micro Devices", "stock"), ("INTC", "Intel Corp.", "stock"),
    ("QCOM", "Qualcomm Inc.", "stock"), ("TXN", "Texas Instruments", "stock"),
    ("MU", "Micron Technology", "stock"), ("ARM", "ARM Holdings", "stock"),
    ("SMCI", "Super Micro Computer", "stock"), ("MRVL", "Marvell Technology", "stock"),
    ("KLAC", "KLA Corp.", "stock"), ("LRCX", "Lam Research", "stock"),
    ("AMAT", "Applied Materials", "stock"), ("SNPS", "Synopsys Inc.", "stock"),
    ("CDNS", "Cadence Design", "stock"), ("ADI", "Analog Devices", "stock"),
    ("NXPI", "NXP Semiconductors", "stock"), ("ON", "ON Semiconductor", "stock"),
    # Cloud / AI / Cyber
    ("CRM", "Salesforce Inc.", "stock"), ("PLTR", "Palantir Technologies", "stock"),
    ("CRWD", "CrowdStrike Holdings", "stock"), ("PANW", "Palo Alto Networks", "stock"),
    ("DDOG", "Datadog Inc.", "stock"), ("SNOW", "Snowflake Inc.", "stock"),
    ("NET", "Cloudflare Inc.", "stock"), ("ZS", "Zscaler Inc.", "stock"),
    ("FTNT", "Fortinet Inc.", "stock"), ("MDB", "MongoDB Inc.", "stock"),
    # Software / SaaS
    ("ADBE", "Adobe Inc.", "stock"), ("NOW", "ServiceNow Inc.", "stock"),
    ("INTU", "Intuit Inc.", "stock"), ("WDAY", "Workday Inc.", "stock"),
    ("SHOP", "Shopify Inc.", "stock"), ("TEAM", "Atlassian Corp.", "stock"),
    ("HUBS", "HubSpot Inc.", "stock"), ("DOCU", "DocuSign Inc.", "stock"),
    ("ZM", "Zoom Video", "stock"), ("OKTA", "Okta Inc.", "stock"),
    # Fintech / Payments
    ("V", "Visa Inc.", "stock"), ("MA", "Mastercard Inc.", "stock"),
    ("PYPL", "PayPal Holdings", "stock"), ("SQ", "Block Inc. (Square)", "stock"),
    ("COIN", "Coinbase Global", "stock"), ("HOOD", "Robinhood Markets", "stock"),
    ("SOFI", "SoFi Technologies", "stock"), ("AFRM", "Affirm Holdings", "stock"),
    ("MSTR", "MicroStrategy", "stock"), ("GPN", "Global Payments", "stock"),
    ("FIS", "Fidelity National Info", "stock"), ("FISV", "Fiserv Inc.", "stock"),
    # Streaming / Media
    ("NFLX", "Netflix Inc.", "stock"), ("DIS", "Walt Disney Co.", "stock"),
    ("CMCSA", "Comcast Corp.", "stock"), ("SPOT", "Spotify Technology", "stock"),
    ("ROKU", "Roku Inc.", "stock"), ("TTD", "The Trade Desk", "stock"),
    # Gaming
    ("EA", "Electronic Arts", "stock"), ("TTWO", "Take-Two Interactive", "stock"),
    ("RBLX", "Roblox Corp.", "stock"), ("U", "Unity Software", "stock"),
    ("DKNG", "DraftKings Inc.", "stock"),
    # Social
    ("SNAP", "Snap Inc.", "stock"), ("PINS", "Pinterest Inc.", "stock"),
    ("MTCH", "Match Group", "stock"),
    # E-commerce
    ("ETSY", "Etsy Inc.", "stock"), ("EBAY", "eBay Inc.", "stock"),
    ("W", "Wayfair Inc.", "stock"), ("CPNG", "Coupang Inc.", "stock"),
    # Financials - Banks
    ("JPM", "JPMorgan Chase", "stock"), ("BAC", "Bank of America", "stock"),
    ("GS", "Goldman Sachs", "stock"), ("MS", "Morgan Stanley", "stock"),
    ("WFC", "Wells Fargo", "stock"), ("C", "Citigroup Inc.", "stock"),
    ("USB", "US Bancorp", "stock"), ("PNC", "PNC Financial", "stock"),
    ("SCHW", "Charles Schwab", "stock"), ("BLK", "BlackRock Inc.", "stock"),
    ("AXP", "American Express", "stock"), ("COF", "Capital One", "stock"),
    ("BRK-B", "Berkshire Hathaway B", "stock"),
    # Insurance / Asset Mgmt
    ("MMC", "Marsh & McLennan", "stock"), ("SPGI", "S&P Global", "stock"),
    ("MCO", "Moody's Corp.", "stock"), ("ICE", "Intercontinental Exchange", "stock"),
    ("CME", "CME Group", "stock"), ("IBKR", "Interactive Brokers", "stock"),
    # Healthcare / Pharma
    ("UNH", "UnitedHealth Group", "stock"), ("JNJ", "Johnson & Johnson", "stock"),
    ("LLY", "Eli Lilly & Co.", "stock"), ("ABBV", "AbbVie Inc.", "stock"),
    ("MRK", "Merck & Co.", "stock"), ("PFE", "Pfizer Inc.", "stock"),
    ("TMO", "Thermo Fisher Scientific", "stock"), ("ABT", "Abbott Laboratories", "stock"),
    ("AMGN", "Amgen Inc.", "stock"), ("GILD", "Gilead Sciences", "stock"),
    ("MRNA", "Moderna Inc.", "stock"), ("BNTX", "BioNTech SE", "stock"),
    ("REGN", "Regeneron Pharma", "stock"), ("VRTX", "Vertex Pharma", "stock"),
    ("ISRG", "Intuitive Surgical", "stock"), ("BMY", "Bristol-Myers Squibb", "stock"),
    ("NVO", "Novo Nordisk", "stock"), ("AZN", "AstraZeneca", "stock"),
    # Biotech small/mid
    ("CRSP", "CRISPR Therapeutics", "stock"), ("EDIT", "Editas Medicine", "stock"),
    ("BEAM", "Beam Therapeutics", "stock"), ("NTLA", "Intellia Therapeutics", "stock"),
    # Consumer / Retail
    ("WMT", "Walmart Inc.", "stock"), ("COST", "Costco Wholesale", "stock"),
    ("HD", "Home Depot", "stock"), ("LOW", "Lowe's Companies", "stock"),
    ("TGT", "Target Corp.", "stock"), ("SBUX", "Starbucks Corp.", "stock"),
    ("MCD", "McDonald's Corp.", "stock"), ("NKE", "Nike Inc.", "stock"),
    ("LULU", "Lululemon Athletica", "stock"), ("KO", "Coca-Cola Co.", "stock"),
    ("PEP", "PepsiCo Inc.", "stock"), ("PG", "Procter & Gamble", "stock"),
    ("CMG", "Chipotle Mexican Grill", "stock"), ("YUM", "Yum! Brands", "stock"),
    ("DPZ", "Domino's Pizza", "stock"), ("CAVA", "CAVA Group", "stock"),
    ("ABNB", "Airbnb Inc.", "stock"), ("BKNG", "Booking Holdings", "stock"),
    ("EXPE", "Expedia Group", "stock"), ("MAR", "Marriott International", "stock"),
    ("HLT", "Hilton Worldwide", "stock"), ("RCL", "Royal Caribbean", "stock"),
    ("ULTA", "Ulta Beauty", "stock"), ("EL", "Estee Lauder", "stock"),
    # Industrial / Defense
    ("BA", "Boeing Co.", "stock"), ("CAT", "Caterpillar Inc.", "stock"),
    ("DE", "Deere & Company", "stock"), ("HON", "Honeywell International", "stock"),
    ("GE", "GE Aerospace", "stock"), ("RTX", "RTX Corp. (Raytheon)", "stock"),
    ("LMT", "Lockheed Martin", "stock"), ("NOC", "Northrop Grumman", "stock"),
    ("GD", "General Dynamics", "stock"), ("AXON", "Axon Enterprise", "stock"),
    ("MMM", "3M Company", "stock"), ("EMR", "Emerson Electric", "stock"),
    # Energy
    ("XOM", "Exxon Mobil", "stock"), ("CVX", "Chevron Corp.", "stock"),
    ("COP", "ConocoPhillips", "stock"), ("SLB", "Schlumberger (SLB)", "stock"),
    ("EOG", "EOG Resources", "stock"), ("OXY", "Occidental Petroleum", "stock"),
    ("ENPH", "Enphase Energy", "stock"), ("FSLR", "First Solar", "stock"),
    # Autos / EV
    ("GM", "General Motors", "stock"), ("F", "Ford Motor", "stock"),
    ("RIVN", "Rivian Automotive", "stock"), ("LCID", "Lucid Group", "stock"),
    ("NIO", "NIO Inc.", "stock"), ("XPEV", "XPeng Inc.", "stock"),
    ("LI", "Li Auto Inc.", "stock"),
    ("UBER", "Uber Technologies", "stock"), ("LYFT", "Lyft Inc.", "stock"),
    # Transport
    ("DAL", "Delta Air Lines", "stock"), ("UAL", "United Airlines", "stock"),
    ("LUV", "Southwest Airlines", "stock"), ("FDX", "FedEx Corp.", "stock"),
    ("UPS", "United Parcel Service", "stock"), ("UNP", "Union Pacific", "stock"),
    # Telecom
    ("T", "AT&T Inc.", "stock"), ("VZ", "Verizon Communications", "stock"),
    ("TMUS", "T-Mobile US", "stock"),
    # Utilities
    ("NEE", "NextEra Energy", "stock"), ("DUK", "Duke Energy", "stock"),
    ("SO", "Southern Company", "stock"),
    # REITs
    ("AMT", "American Tower", "stock"), ("PLD", "Prologis Inc.", "stock"),
    ("CCI", "Crown Castle", "stock"), ("EQIX", "Equinix Inc.", "stock"),
    ("SPG", "Simon Property Group", "stock"), ("O", "Realty Income", "stock"),
    ("DLR", "Digital Realty", "stock"),
    # Materials
    ("LIN", "Linde plc", "stock"), ("SHW", "Sherwin-Williams", "stock"),
    ("FCX", "Freeport-McMoRan", "stock"), ("NEM", "Newmont Corp.", "stock"),
    ("NUE", "Nucor Corp.", "stock"), ("AA", "Alcoa Corp.", "stock"),
    # Other US
    ("CSCO", "Cisco Systems", "stock"), ("IBM", "IBM Corp.", "stock"),
    ("ACN", "Accenture plc", "stock"), ("DELL", "Dell Technologies", "stock"),
    ("DASH", "DoorDash Inc.", "stock"),
    # Chinese ADRs
    ("BABA", "Alibaba Group", "stock"), ("JD", "JD.com Inc.", "stock"),
    ("PDD", "PDD Holdings (Temu)", "stock"), ("BIDU", "Baidu Inc.", "stock"),
    ("BILI", "Bilibili Inc.", "stock"), ("TME", "Tencent Music", "stock"),
    # ── ETFs – Index ──
    ("SPY", "SPDR S&P 500 ETF", "etf"), ("VOO", "Vanguard S&P 500 ETF", "etf"),
    ("QQQ", "Invesco Nasdaq 100 ETF", "etf"), ("IWM", "iShares Russell 2000 ETF", "etf"),
    ("DIA", "SPDR Dow Jones ETF", "etf"), ("VTI", "Vanguard Total Stock Market", "etf"),
    ("VT", "Vanguard Total World Stock", "etf"), ("RSP", "Invesco S&P 500 Equal Weight", "etf"),
    # ETFs – Sector
    ("XLF", "Financial Select Sector SPDR", "etf"), ("XLE", "Energy Select Sector SPDR", "etf"),
    ("XLV", "Health Care Select Sector SPDR", "etf"), ("XLK", "Technology Select Sector SPDR", "etf"),
    ("XLI", "Industrial Select Sector SPDR", "etf"), ("XLU", "Utilities Select Sector SPDR", "etf"),
    ("SOXX", "iShares Semiconductor ETF", "etf"), ("SMH", "VanEck Semiconductor ETF", "etf"),
    ("XBI", "SPDR S&P Biotech ETF", "etf"), ("KRE", "SPDR S&P Regional Banking ETF", "etf"),
    # ETFs – Thematic
    ("ARKK", "ARK Innovation ETF", "etf"), ("ARKW", "ARK Next Gen Internet ETF", "etf"),
    ("ARKG", "ARK Genomic Revolution ETF", "etf"),
    ("HACK", "ETFMG Prime Cyber Security ETF", "etf"),
    ("TAN", "Invesco Solar ETF", "etf"), ("LIT", "Global X Lithium & Battery ETF", "etf"),
    ("BOTZ", "Global X Robotics & AI ETF", "etf"),
    # ETFs – International
    ("EWJ", "iShares MSCI Japan ETF", "etf"), ("EWG", "iShares MSCI Germany ETF", "etf"),
    ("EWU", "iShares MSCI United Kingdom ETF", "etf"),
    ("FXI", "iShares China Large-Cap ETF", "etf"), ("KWEB", "KraneShares China Internet ETF", "etf"),
    ("EEM", "iShares MSCI Emerging Markets ETF", "etf"), ("VWO", "Vanguard FTSE Emerging Markets ETF", "etf"),
    ("EFA", "iShares MSCI EAFE ETF", "etf"), ("EWZ", "iShares MSCI Brazil ETF", "etf"),
    ("INDA", "iShares MSCI India ETF", "etf"),
    # ETFs – Fixed income / Commodities / Leveraged
    ("TLT", "iShares 20+ Year Treasury ETF", "etf"), ("BND", "Vanguard Total Bond Market ETF", "etf"),
    ("HYG", "iShares High Yield Corp Bond ETF", "etf"), ("AGG", "iShares Core US Aggregate Bond ETF", "etf"),
    ("GLD", "SPDR Gold Shares", "etf"), ("SLV", "iShares Silver Trust", "etf"),
    ("GDX", "VanEck Gold Miners ETF", "etf"), ("USO", "United States Oil Fund", "etf"),
    ("IBIT", "iShares Bitcoin Trust ETF", "etf"), ("BITO", "ProShares Bitcoin Strategy ETF", "etf"),
    ("TQQQ", "ProShares UltraPro QQQ (3x)", "etf"), ("SQQQ", "ProShares UltraPro Short QQQ (-3x)", "etf"),
    ("SOXL", "Direxion Semiconductor Bull 3x", "etf"), ("SOXS", "Direxion Semiconductor Bear 3x", "etf"),
    ("UVXY", "ProShares Ultra VIX Short-Term", "etf"),
    # ETFs – European / Precious Metals
    ("ISLN.L", "iShares Physical Silver ETC", "etf"), ("PPFB.DE", "iShares Physical Metals (Xetra)", "etf"),
    ("PHAG.AS", "WisdomTree Physical Silver", "etf"),
    ("ASML", "ASML Holding NV", "stock"), ("SAP", "SAP SE", "stock"),
    # ── Europe ──
    ("MC.PA", "LVMH Moet Hennessy", "stock"), ("OR.PA", "L'Oreal SA", "stock"),
    ("AIR.PA", "Airbus SE", "stock"), ("SIE.DE", "Siemens AG", "stock"),
    ("ALV.DE", "Allianz SE", "stock"), ("BMW.DE", "BMW AG", "stock"),
    ("VOW3.DE", "Volkswagen AG", "stock"), ("MBG.DE", "Mercedes-Benz Group", "stock"),
    ("BAS.DE", "BASF SE", "stock"), ("BAYN.DE", "Bayer AG", "stock"),
    ("NESN.SW", "Nestle SA", "stock"), ("ROG.SW", "Roche Holding", "stock"),
    ("NOVN.SW", "Novartis AG", "stock"), ("UBSG.SW", "UBS Group AG", "stock"),
    ("SHEL", "Shell plc", "stock"), ("BP.L", "BP plc", "stock"),
    ("HSBA.L", "HSBC Holdings", "stock"), ("ULVR.L", "Unilever plc", "stock"),
    ("GSK.L", "GSK plc", "stock"), ("RIO.L", "Rio Tinto", "stock"),
    ("BARC.L", "Barclays plc", "stock"), ("LSEG.L", "London Stock Exchange Group", "stock"),
    ("SAN", "Banco Santander", "stock"), ("BBVA", "BBVA SA", "stock"),
    ("TEF.MC", "Telefonica SA", "stock"), ("ITX.MC", "Inditex (Zara)", "stock"),
    ("RACE.MI", "Ferrari NV", "stock"), ("ENEL.MI", "Enel SpA", "stock"),
    ("ENI.MI", "Eni SpA", "stock"), ("UCG.MI", "UniCredit SpA", "stock"),
    ("ERIC-B.ST", "Ericsson", "stock"), ("VOLV-B.ST", "Volvo AB", "stock"),
    ("EQNR.OL", "Equinor ASA", "stock"), ("NOVO-B.CO", "Novo Nordisk (Copenhagen)", "stock"),
    # ── Asia / Pacific ──
    ("TSM", "Taiwan Semiconductor (ADR)", "stock"), ("TM", "Toyota Motor (ADR)", "stock"),
    ("SONY", "Sony Group (ADR)", "stock"), ("HMC", "Honda Motor (ADR)", "stock"),
    ("NTDOY", "Nintendo (OTC ADR)", "stock"), ("MUFG", "Mitsubishi UFJ Financial", "stock"),
    ("INFY", "Infosys Ltd. (ADR)", "stock"), ("WIT", "Wipro Ltd. (ADR)", "stock"),
    ("HDB", "HDFC Bank (ADR)", "stock"), ("IBN", "ICICI Bank (ADR)", "stock"),
    ("SE", "Sea Limited", "stock"), ("GRAB", "Grab Holdings", "stock"),
    ("BHP", "BHP Group", "stock"),
    # ── LATAM ──
    ("MELI", "MercadoLibre Inc.", "stock"), ("NU", "Nu Holdings (Nubank)", "stock"),
    ("VALE", "Vale SA (ADR)", "stock"), ("PBR", "Petrobras (ADR)", "stock"),
    ("ITUB", "Itau Unibanco (ADR)", "stock"), ("ABEV", "Ambev SA (ADR)", "stock"),
    ("GLOB", "Globant SA", "stock"), ("YPF", "YPF SA (ADR)", "stock"),
    ("GGAL", "Grupo Financiero Galicia", "stock"), ("AMX", "America Movil", "stock"),
    ("SQM", "SQM (Sociedad Quimica y Minera)", "stock"),
    # ── Crypto ──
    ("BTC", "Bitcoin", "crypto"), ("ETH", "Ethereum", "crypto"),
    ("SOL", "Solana", "crypto"), ("XRP", "Ripple (XRP)", "crypto"),
    ("ADA", "Cardano", "crypto"), ("DOT", "Polkadot", "crypto"),
    ("AVAX", "Avalanche", "crypto"), ("MATIC", "Polygon (MATIC)", "crypto"),
    ("LINK", "Chainlink", "crypto"), ("UNI", "Uniswap", "crypto"),
    ("ATOM", "Cosmos", "crypto"), ("NEAR", "NEAR Protocol", "crypto"),
    ("SUI", "Sui", "crypto"), ("APT", "Aptos", "crypto"),
    ("INJ", "Injective", "crypto"), ("SEI", "Sei Network", "crypto"),
    ("ARB", "Arbitrum", "crypto"), ("OP", "Optimism", "crypto"),
    ("RNDR", "Render Token", "crypto"), ("FET", "Fetch.ai", "crypto"),
    ("GRT", "The Graph", "crypto"), ("IMX", "Immutable X", "crypto"),
    ("TON", "Toncoin", "crypto"), ("TRX", "TRON", "crypto"),
    ("BNB", "Binance Coin", "crypto"), ("LTC", "Litecoin", "crypto"),
    ("BCH", "Bitcoin Cash", "crypto"), ("HBAR", "Hedera", "crypto"),
    ("ICP", "Internet Computer", "crypto"), ("FIL", "Filecoin", "crypto"),
    ("AAVE", "Aave", "crypto"), ("MKR", "Maker", "crypto"),
    ("LDO", "Lido DAO", "crypto"), ("CRV", "Curve DAO", "crypto"),
    ("DYDX", "dYdX", "crypto"), ("GMX", "GMX", "crypto"),
    ("PENDLE", "Pendle", "crypto"), ("JUP", "Jupiter (Solana)", "crypto"),
    # Memecoins
    ("DOGE", "Dogecoin", "crypto"), ("SHIB", "Shiba Inu", "crypto"),
    ("PEPE", "Pepe", "crypto"), ("WIF", "dogwifhat", "crypto"),
    ("BONK", "Bonk", "crypto"), ("FLOKI", "Floki Inu", "crypto"),
    ("TRUMP", "Official Trump", "crypto"), ("MEME", "Memecoin", "crypto"),
    ("POPCAT", "Popcat", "crypto"), ("BRETT", "Brett", "crypto"),
    ("TURBO", "Turbo", "crypto"), ("NEIRO", "Neiro", "crypto"),
    # ── Commodities ──
    ("GOLD", "Gold", "commodity"), ("SILVER", "Silver", "commodity"),
    ("PLATINUM", "Platinum", "commodity"), ("PALLADIUM", "Palladium", "commodity"),
    ("COPPER", "Copper", "commodity"),
    ("OIL", "Crude Oil WTI", "commodity"), ("BRENT", "Brent Crude", "commodity"),
    ("NATGAS", "Natural Gas", "commodity"),
    ("WHEAT", "Wheat", "commodity"), ("CORN", "Corn", "commodity"),
    ("SOYBEAN", "Soybeans", "commodity"), ("COFFEE", "Coffee", "commodity"),
    ("SUGAR", "Sugar", "commodity"), ("COCOA", "Cocoa", "commodity"),
    ("COTTON", "Cotton", "commodity"), ("CATTLE", "Live Cattle", "commodity"),
]


@router.get("/search")
async def search_symbols(
    q: str = Query(description="Search query", min_length=1),
    limit: int = Query(default=10, ge=1, le=30),
):
    """Search symbols by ticker or name for autocomplete."""
    query = q.upper()
    results = []
    # Exact prefix on symbol gets highest priority
    for sym, name, asset_type in _SYMBOL_CATALOG:
        if sym.upper().startswith(query):
            results.append({"symbol": sym, "name": name, "type": asset_type, "match": "symbol"})
    # Then name matches
    query_lower = q.lower()
    for sym, name, asset_type in _SYMBOL_CATALOG:
        if query_lower in name.lower() and not sym.upper().startswith(query):
            results.append({"symbol": sym, "name": name, "type": asset_type, "match": "name"})
    return {"results": results[:limit], "query": q}


@router.get("/movers")
async def get_movers(
    region: str = Query(default="us", description="Market region: all, us, eu, asia, latam, crypto"),
    threshold: float = Query(default=1.0, description="Minimum change percent"),
):
    """Get top gainers and losers with sparkline data."""
    region_symbols: dict[str, list[str]] = {
        "us": [
            # ── Mega-cap tech ──
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
            # ── Semiconductors ──
            "AMD", "INTC", "QCOM", "MU", "ARM", "SMCI", "MRVL", "AMAT", "LRCX",
            # ── Cybersecurity / Cloud / AI ──
            "CRWD", "PANW", "NET", "PLTR", "DDOG", "SNOW", "MDB", "SOUN", "AI",
            # ── Software / SaaS ──
            "CRM", "ADBE", "NOW", "INTU", "HUBS", "TEAM", "MNDY", "TOST", "ZM",
            # ── Fintech / payments ──
            "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "SOFI", "AFRM", "MSTR",
            # ── E-commerce / consumer internet ──
            "SHOP", "ETSY", "PINS", "SNAP", "RBLX", "DKNG",
            # ── Streaming / media ──
            "NFLX", "DIS", "SPOT", "ROKU", "TTD", "CMCSA",
            # ── ETFs – broad market ──
            "SPY", "QQQ", "IWM", "DIA", "VTI",
            # ── ETFs – sector / thematic ──
            "XLF", "XLE", "XLV", "XLK", "ARKK", "SOXX", "SMH",
            "GLD", "SLV", "IBIT", "SOXL", "TQQQ",
            # ── Financials ──
            "JPM", "BAC", "GS", "MS", "WFC", "C", "BRK-B", "SCHW", "BLK",
            # ── Healthcare / pharma / biotech ──
            "UNH", "LLY", "JNJ", "ABBV", "MRK", "PFE", "MRNA", "ISRG",
            "REGN", "VRTX", "AMGN", "GILD", "CRSP", "DXCM",
            # ── Consumer / retail ──
            "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "LULU", "CMG",
            "ABNB", "BKNG", "RCL", "CCL",
            # ── Industrial / defense ──
            "BA", "CAT", "HON", "GE", "RTX", "LMT", "DE", "AXON",
            # ── Transport / logistics ──
            "DAL", "UAL", "FDX", "UPS", "UBER", "LYFT",
            # ── Energy ──
            "XOM", "CVX", "COP", "OXY", "SLB", "ENPH", "FSLR", "CEG", "VST",
            # ── Autos / EV ──
            "GM", "F", "RIVN", "LCID",
            # ── Chinese ADRs ──
            "BABA", "JD", "PDD", "BIDU", "NIO", "LI",
            # ── Telecom / utilities / REITs ──
            "T", "VZ", "TMUS", "NEE", "AMT", "EQIX", "O", "DLR",
            # ── Materials ──
            "LIN", "FCX", "NEM", "NUE", "CLF", "X",
            # ── Other notable ──
            "CSCO", "IBM", "DELL", "DASH",
        ],
        "eu": [
            # ── Germany ──
            "SAP", "SIE.DE", "ALV.DE", "BMW.DE", "MBG.DE", "BAS.DE", "IFX.DE",
            "DBK.DE", "DTE.DE", "RWE.DE", "DHL.DE",
            # ── France ──
            "MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "BNP.PA", "AIR.PA",
            "SU.PA", "KER.PA", "STM.PA", "CAP.PA",
            # ── Netherlands ──
            "ASML", "PHIA.AS", "UNA.AS", "INGA.AS", "BESI.AS", "PRX.AS",
            # ── Nordic ──
            "NVO", "NOVO-B.CO", "ERIC-B.ST", "VOLV-B.ST", "NOKIA.HE",
            "EQNR.OL", "NHY.OL",
            # ── UK ──
            "SHEL", "AZN", "HSBA.L", "BP.L", "RIO.L", "GSK.L",
            "BARC.L", "LLOY.L", "LSEG.L", "GLEN.L",
            # ── Switzerland ──
            "NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW",
            # ── Spain / Italy ──
            "SAN", "BBVA", "UCG.MI", "ENEL.MI", "ENI.MI",
            # ── EU ETFs ──
            "FEZ", "VGK", "EWG", "EWU",
        ],
        "asia": [
            # ── Japan ──
            "TM", "SONY", "NTDOY", "MUFG", "9984.T", "7203.T", "6758.T",
            "8035.T", "7974.T", "6861.T",
            # ── China / Hong Kong ──
            "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI",
            "9988.HK", "0700.HK", "3690.HK", "1211.HK", "0005.HK",
            # ── Taiwan / Korea ──
            "TSM", "2330.TW", "005930.KS", "000660.KS",
            # ── India ──
            "INFY", "HDB", "IBN", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
            # ── Southeast Asia / Australia ──
            "SE", "GRAB", "DBS.SI", "BHP", "CBA.AX", "CSL.AX",
            # ── Asia ETFs ──
            "EWJ", "EWT", "EWY", "FXI", "KWEB", "INDA",
        ],
        "latam": [
            # ── Brazil ──
            "VALE", "PBR", "ITUB", "NU", "ABEV", "XP", "PAGS", "STNE",
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "B3SA3.SA", "WEGE3.SA",
            # ── Argentina ──
            "MELI", "GLOB", "YPF", "GGAL", "BMA", "PAM",
            # ── Mexico ──
            "AMX", "FEMSA", "KOF", "CEMEXCPO.MX", "WALMEX.MX",
            # ── Chile / Colombia / Peru ──
            "SQM", "BSAC", "EC", "COPA", "BAP",
            # ── LATAM ETFs ──
            "EWZ", "EWW", "ILF",
        ],
        "crypto": [
            # ── Major / Layer 1 ──
            "BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "MATIC", "ATOM",
            "XRP", "BNB", "TRX", "TON", "NEAR", "SUI", "APT", "SEI", "INJ",
            "FTM", "ALGO", "HBAR", "ICP", "FIL",
            # ── DeFi ──
            "LINK", "UNI", "AAVE", "MKR", "LDO", "CRV", "COMP", "PENDLE",
            # ── Layer 2 / Infrastructure ──
            "ARB", "OP", "IMX", "RNDR", "GRT", "FET",
            # ── Other major ──
            "LTC", "BCH", "XLM", "SAND", "MANA",
            # ── Memecoins ──
            "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "TRUMP",
        ],
    }

    if region == "all":
        seen: set[str] = set()
        symbols: list[str] = []
        for syms in region_symbols.values():
            for s in syms:
                if s not in seen:
                    seen.add(s)
                    symbols.append(s)
    else:
        symbols = region_symbols.get(region, region_symbols["us"])

    # Check endpoint-level cache
    cache_key = f"{region}:{threshold}"
    cached = _movers_cache.get(cache_key)
    if cached:
        ts, data = cached
        if time.time() - ts < _MOVERS_CACHE_TTL:
            return data

    data = await market_data_service.get_extended_movers(symbols=symbols, threshold=threshold)
    _movers_cache[cache_key] = (time.time(), data)
    return data


@router.get("/commodities")
async def get_commodities():
    """Get all commodities with current prices, grouped by category."""
    import asyncio

    async def _fetch_one(symbol: str, info: dict) -> dict | None:
        quote = await market_data_service.get_commodity_quote(symbol)
        if not quote:
            return None
        return {
            "symbol": symbol,
            "name": info["name"],
            "category": info["category"],
            "price": quote.get("price", 0),
            "change_percent": quote.get("change_percent", 0),
            "volume": quote.get("volume", 0),
        }

    tasks = [_fetch_one(sym, info) for sym, info in COMMODITY_FUTURES_MAP.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items = [r for r in results if isinstance(r, dict)]

    grouped: dict[str, list] = {}
    for item in items:
        cat = item["category"]
        grouped.setdefault(cat, []).append(item)

    return {"commodities": items, "by_category": grouped}


@router.get("/quote/{symbol}", response_model=AssetQuote)
async def get_quote(
    symbol: str,
    asset_type: AssetType | None = Query(default=None, description="Asset type hint"),
):
    """Get real-time quote for a single asset."""
    quote = await market_data_service.get_quote(symbol, asset_type)
    if not quote:
        raise HTTPException(status_code=404, detail=f"No data found for '{symbol.upper()}'")
    # Sanitize None values to defaults for Pydantic
    for key in ("volume", "previous_close", "market_cap", "change_percent"):
        if quote.get(key) is None:
            quote[key] = 0.0
    return AssetQuote(**quote)


@router.get("/sparklines")
async def get_sparklines(
    symbols: str = Query(description="Comma-separated list of symbols (max 30)"),
    days: int = Query(default=7, ge=1, le=30, description="Number of days"),
):
    """Return closing prices for the last N days for multiple symbols (for sparkline charts)."""
    import asyncio

    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]

    async def _fetch_one(sym: str) -> tuple[str, list[float]]:
        try:
            records = await market_data_service.get_history(sym, period="1mo", interval="1d")
            if not records:
                return (sym, [])
            closes = [r["close"] for r in records[-days:]]
            return (sym, closes)
        except Exception:
            return (sym, [])

    results = await asyncio.gather(*[_fetch_one(s) for s in sym_list])
    return {sym: closes for sym, closes in results}


@router.get("/history/{symbol}", response_model=HistoricalData)
async def get_history(
    symbol: str,
    period: str = Query(default="1mo", description="Time period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,ytd,max"),
    interval: str = Query(default="1d", description="Interval: 1m,5m,15m,30m,1h,1d,1wk,1mo"),
):
    """Get historical OHLCV data for a stock/ETF."""
    records = await market_data_service.get_history(symbol, period=period, interval=interval)
    if not records:
        raise HTTPException(status_code=404, detail=f"No history found for '{symbol.upper()}'")

    data_points = [HistoricalDataPoint(**r) for r in records]
    return HistoricalData(symbol=symbol.upper(), period=period, interval=interval, data=data_points)


@router.get("/analysis/{symbol}", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    symbol: str,
    period: str = Query(default="6mo", description="History period for analysis"),
):
    """Compute technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands) for an asset."""
    records = await market_data_service.get_history(symbol, period=period, interval="1d")
    if not records or len(records) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for technical analysis on '{symbol.upper()}'"
        )

    closes = [r["close"] for r in records]
    indicators = compute_all_indicators(closes)

    return TechnicalAnalysis(
        symbol=symbol.upper(),
        rsi=RSIIndicator(**indicators["rsi"]),
        macd=MACDIndicator(**indicators["macd"]),
        sma=SMAIndicator(**indicators["sma"]),
        ema=EMAIndicator(**indicators["ema"]),
        bollinger_bands=BollingerBandsIndicator(**indicators["bollinger_bands"]),
        overall_signal=indicators["overall_signal"],
        signal_counts=indicators["signal_counts"],
    )


@router.get("/score/{symbol}", response_model=AssetScoreResponse)
async def get_asset_score(
    symbol: str,
    asset_type: AssetType | None = Query(default=None, description="Asset type hint"),
    user: AuthUser = Depends(get_current_user),
):
    """Get explainable structured scoring for an asset."""
    result = await build_asset_score(
        symbol,
        asset_type=asset_type.value if asset_type else None,
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
    return AssetScoreResponse(**result)


@router.get("/signal-summary/{symbol}", response_model=SignalSummary)
async def get_signal_summary(symbol: str):
    """Get aggregated signal summary with oscillator and MA breakdown."""
    records = await market_data_service.get_history(symbol, period="6mo", interval="1d")
    if not records or len(records) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for signal analysis on '{symbol.upper()}'"
        )

    closes = [r["close"] for r in records]
    indicators = compute_all_indicators(closes)
    price = closes[-1] if closes else None

    return build_signal_summary(symbol, indicators, price)


@router.get("/volatility/{symbol}")
async def get_volatility(symbol: str):
    """Get volatility metrics for an asset."""
    records = await market_data_service.get_history(symbol, period="6mo", interval="1d")
    if not records or len(records) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for volatility analysis on '{symbol.upper()}'"
        )

    quote = await market_data_service.get_quote(symbol)
    current_price = quote["price"] if quote else records[-1]["close"]

    result = compute_volatility(symbol.upper(), records, current_price)
    return result


@router.get("/macro", response_model=MacroIntelligenceResponse)
async def get_macro_intelligence():
    """Get macro economic indicators (VIX, DXY, Treasury yields, Gold, Oil) with analysis."""
    raw_indicators = await get_all_macro_indicators()
    summary = get_macro_summary(raw_indicators)
    macro_context = await get_macro_context()

    indicators = [MacroIndicatorDetail(**m) for m in raw_indicators]

    return MacroIntelligenceResponse(
        indicators=indicators,
        summary=MacroSummary(**summary),
        sources=macro_context.get("sources", []),
        official_series=macro_context.get("official_series", []),
        fear_greed=macro_context.get("fear_greed"),
    )


@router.get("/sentiment/{symbol}", response_model=SentimentAnalysisResponse)
async def get_sentiment(
    symbol: str,
    asset_type: AssetType | None = Query(default=None, description="Asset type hint"),
):
    """Get AI-powered sentiment analysis for an asset, enriched with social media data."""
    import asyncio

    symbol_upper = symbol.upper()

    # Fetch quote, history, and social data in parallel
    quote_task = market_data_service.get_quote(symbol_upper, asset_type)
    history_task = market_data_service.get_history(symbol_upper, period="6mo", interval="1d")
    social_task = news_service.get_social_sentiment(symbol_upper)

    quote, records, social_data = await asyncio.gather(
        quote_task, history_task, social_task, return_exceptions=True,
    )

    quote_data = dict(quote) if isinstance(quote, dict) else None
    technical_data = None
    if isinstance(records, list) and len(records) >= 30:
        closes = [r["close"] for r in records]
        technical_data = compute_all_indicators(closes)

    social = social_data if isinstance(social_data, dict) else None

    asset_type_str = asset_type.value if asset_type else "stock"
    result = await analyze_sentiment(
        symbol=symbol_upper,
        asset_type=asset_type_str,
        quote_data=quote_data,
        technical_data=technical_data,
        social_data=social,
    )

    return SentimentAnalysisResponse(**result)


@router.get("/social-sentiment/{symbol}")
async def get_social_sentiment(symbol: str):
    """Get social media sentiment (Reddit + Twitter) for a symbol via Finnhub."""
    data = await news_service.get_social_sentiment(symbol) if news_service.is_configured else None
    if data:
        data["configured"] = True
        return data

    feed = await get_ai_analyzed_feed(limit=60)
    fallback = build_social_sentiment_from_articles(symbol, feed.get("articles", []))
    fallback["configured"] = False
    return fallback


@router.get("/enhanced-sentiment/{symbol}")
async def get_enhanced_sentiment(symbol: str):
    """Get multi-source enhanced sentiment (AI + Social + News) for a symbol."""
    from app.services.enhanced_sentiment_service import get_enhanced_sentiment as fetch_enhanced
    try:
        return await fetch_enhanced(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced sentiment error: {e}")


@router.get("/currencies")
async def get_currencies():
    """Get list of supported currencies."""
    from app.services.currency_service import get_supported_currencies
    return {"currencies": get_supported_currencies()}


@router.get("/convert")
async def convert_currency(
    amount: float = Query(description="Amount to convert"),
    from_currency: str = Query(default="USD", alias="from"),
    to_currency: str = Query(default="EUR", alias="to"),
):
    """Convert between currencies using Frankfurter API."""
    from app.services.currency_service import convert_currency as do_convert
    result = await do_convert(amount, from_currency, to_currency)
    if result is None:
        raise HTTPException(status_code=400, detail="Currency conversion failed")
    return result


@router.get("/fundamentals/{symbol}", response_model=FundamentalsResponse)
async def get_fundamentals(symbol: str):
    """Get fundamental data (ratios, growth, peers) for a symbol."""
    from app.services.fundamentals_service import get_fundamentals as fetch_fundamentals
    result = await fetch_fundamentals(symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"No fundamentals for '{symbol.upper()}'")
    return FundamentalsResponse(**result)


@router.get("/calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar(
    start_date: str = Query(default="", description="Start date YYYY-MM-DD"),
    end_date: str = Query(default="", description="End date YYYY-MM-DD"),
):
    """Get economic calendar events and upcoming earnings."""
    from app.services.economic_calendar import fetch_economic_calendar
    result = await fetch_economic_calendar(start_date, end_date)
    return EconomicCalendarResponse(**result)


@router.get("/filings/{symbol}", response_model=FilingsResponse)
async def get_filings(symbol: str):
    """Get recent SEC filings for a symbol."""
    from app.services.sec_service import get_company_filings

    return FilingsResponse(**(await get_company_filings(symbol)))


@router.get("/insiders/{symbol}", response_model=InsiderActivityResponse)
async def get_insider_activity(symbol: str):
    """Get recent insider activity for a symbol."""
    from app.services.insider_service import get_insider_activity

    return InsiderActivityResponse(**(await get_insider_activity(symbol)))


@router.get("/sectors/heatmap", response_model=SectorHeatmapResponse)
async def get_sector_heatmap():
    """Get sector performance heatmap data."""
    from app.services.sector_heatmap import get_sector_performance
    result = await get_sector_performance()
    return SectorHeatmapResponse(**result)


@router.get("/breadth", response_model=MarketBreadthIndicators)
async def get_market_breadth():
    """Get market breadth indicators (advance/decline, % above SMA)."""
    from app.services.sector_heatmap import get_market_breadth as fetch_breadth
    result = await fetch_breadth()
    return MarketBreadthIndicators(**result)
