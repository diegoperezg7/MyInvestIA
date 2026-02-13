from fastapi import APIRouter, HTTPException, Query

from app.schemas.asset import (
    Asset,
    AssetQuote,
    AssetType,
    BollingerBandsIndicator,
    EMAIndicator,
    HistoricalData,
    HistoricalDataPoint,
    MACDIndicator,
    MacroIndicator,
    MacroIndicatorDetail,
    MacroIntelligenceResponse,
    MacroSummary,
    MarketOverview,
    RSIIndicator,
    SMAIndicator,
    SentimentAnalysisResponse,
    TechnicalAnalysis,
)
from app.schemas.signals import SignalSummary
from app.services.macro_intelligence import get_all_macro_indicators, get_macro_summary
from app.services.market_data import COMMODITY_FUTURES_MAP, market_data_service
from app.services.news_service import news_service
from app.services.provider_chain import provider_chain
from app.services.sentiment_service import analyze_sentiment
from app.services.signal_aggregator import build_signal_summary
from app.services.technical_analysis import compute_all_indicators
from app.services.volatility_service import compute_volatility

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/", response_model=MarketOverview)
async def get_market_overview():
    """Get market overview with top movers from major stocks."""
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

    # Fetch macro indicators for the overview
    macro_raw = await get_all_macro_indicators()
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
        sentiment_index=0.0,
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
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
            # ── Semiconductors ──
            "AMD", "INTC", "QCOM", "TXN", "MU", "MRVL", "KLAC", "LRCX", "AMAT", "SNPS",
            "CDNS", "ARM", "SMCI", "ON", "NXPI", "ADI", "MCHP", "SWKS", "MPWR", "WOLF",
            "GFS", "CRUS", "RMBS", "ACLS", "ONTO",
            # ── Cybersecurity / infra ──
            "CRWD", "PANW", "FTNT", "ZS", "NET", "S", "RPD", "TENB", "QLYS", "VRNS",
            # ── Cloud / data / AI ──
            "PLTR", "DDOG", "SNOW", "MDB", "CFLT", "ESTC", "GTLB", "FROG", "AUR",
            "PATH", "AI", "BBAI", "SOUN", "IOSP",
            # ── Software / SaaS ──
            "CRM", "ADBE", "NOW", "INTU", "WDAY", "TEAM", "HUBS", "DOCU", "ZM",
            "OKTA", "ZI", "BILL", "PCOR", "MNDY", "TOST", "BRZE", "ALTR", "CWAN",
            # ── Fintech / payments ──
            "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "SOFI", "AFRM", "MSTR", "UPST",
            "FOUR", "FLYW", "PAYO", "GPN", "FIS", "FISV", "FI", "WEX",
            # ── E-commerce / consumer internet ──
            "SHOP", "AMZN", "ETSY", "EBAY", "W", "CHWY", "CARG", "CPNG",
            "PINS", "SNAP", "MTCH", "BMBL",
            # ── Gaming / metaverse ──
            "U", "RBLX", "EA", "TTWO", "ATVI", "DKNG", "PENN", "RSI",
            # ── Streaming / media / entertainment ──
            "NFLX", "DIS", "CMCSA", "WBD", "PARA", "SPOT", "ROKU", "TTD",
            "IMAX", "LGF-A", "MSGS", "LYV", "SIRI",
            # ── Social / advertising ──
            "GOOGL", "META", "TTD", "MGNI", "PUBM", "DSP", "IAS", "DV",
            # ── ETFs – broad market ──
            "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VT", "VXUS",
            "MDY", "IJR", "RSP", "SPLG", "SCHB", "ITOT",
            # ── ETFs – sector ──
            "XLF", "XLE", "XLV", "XLK", "XLI", "XLU", "XLP", "XLY", "XLB", "XLRE",
            "XBI", "XHB", "XRT", "XME", "XOP", "KRE", "KBE",
            # ── ETFs – thematic / factor ──
            "ARKK", "ARKW", "ARKG", "ARKF", "ARKQ",
            "SOXX", "SMH", "HACK", "BOTZ", "ROBO", "LIT", "TAN", "ICLN", "QCLN",
            "KWEB", "CQQQ", "FXI", "EEM", "VWO", "EFA", "IEMG",
            # ── ETFs – fixed income / commodities / leveraged ──
            "TLT", "IEF", "SHY", "BND", "AGG", "HYG", "LQD", "JNK", "BNDX", "TIP",
            "GLD", "SLV", "GDX", "GDXJ", "USO", "UNG", "DBA", "PALL",
            "IBIT", "BITO", "GBTC", "ETHE",
            "TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UPRO", "SDS",
            "UVXY", "VXX", "SVXY",
            # ── Financials – banks ──
            "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF",
            "SCHW", "BK", "STT", "FITB", "HBAN", "KEY", "RF", "CFG", "MTB", "ZION",
            "SIVB", "WAL", "FRC", "ALLY", "DFS", "SYF", "NYCB",
            # ── Financials – insurance / asset management ──
            "BRK-B", "BLK", "AXP", "MMC", "AON", "AJG", "SPGI", "MCO", "MSCI",
            "ICE", "CME", "CBOE", "NDAQ", "TW", "LPLA", "RJF", "IBKR", "HOOD",
            "AIG", "MET", "PRU", "ALL", "TRV", "PGR", "CB", "AFL", "HIG",
            # ── Healthcare – pharma / biotech ──
            "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "AMGN", "GILD",
            "BIIB", "REGN", "VRTX", "BMY", "AZN", "NVO", "GSK", "SNY", "MRNA", "BNTX",
            "ZTS", "CI", "ELV", "HUM", "CNC", "MOH", "ALGN", "DXCM", "PODD",
            # ── Healthcare – devices / services ──
            "ISRG", "MDT", "SYK", "BSX", "EW", "BDX", "BAX", "ZBH",
            "HOLX", "IDXX", "IQV", "A", "WAT", "MTD", "TFX",
            "HCA", "THC", "UHS", "DVA", "ENSG", "AMED",
            # ── Biotech – small/mid cap ──
            "SGEN", "ALNY", "EXAS", "RARE", "BMRN", "INCY", "IONS", "SRPT",
            "PCVX", "RCKT", "ARWR", "NTLA", "BEAM", "CRSP", "EDIT", "VERV",
            "ACAD", "HALO", "NBIX", "CRNX", "RVMD", "LEGN", "IMVT",
            # ── Consumer / retail ──
            "WMT", "COST", "HD", "LOW", "TGT", "SBUX", "MCD", "NKE", "LULU", "TJX",
            "KO", "PEP", "PG", "CL", "KMB", "MNST", "KDP", "STZ", "TAP", "SAM",
            "DG", "DLTR", "ROST", "BURL", "GPS", "ANF", "AEO", "URBN", "TPR", "CPRI",
            "EL", "DECK", "CROX", "BIRK", "ON", "SKX",
            "ULTA", "COTY", "HELE",
            "CMG", "YUM", "DPZ", "WEN", "QSR", "JACK", "WING", "CAVA", "SHAK",
            "ABNB", "BKNG", "EXPE", "MAR", "HLT", "H", "IHG", "WH", "RCL", "CCL", "NCLH",
            # ── Industrial / defense ──
            "BA", "CAT", "DE", "HON", "GE", "RTX", "LMT", "NOC", "GD", "HII", "LHX",
            "TDG", "HWM", "AXON", "TXT", "LDOS", "SAIC", "BAH",
            "MMM", "EMR", "ROK", "AME", "ITW", "PH", "DOV", "IR", "SWK",
            "ETN", "CMI", "PCAR", "GNRC", "TT", "A", "OTIS", "CARR",
            "WM", "RSG", "WCN", "CLH", "SRCL",
            "FLR", "PWR", "FAST", "WSO", "AOS", "RRX",
            # ── Aerospace / transport / logistics ──
            "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "HA", "SAVE",
            "FDX", "UPS", "XPO", "CHRW", "JBHT", "ODFL", "SAIA", "KNX",
            "UNP", "CSX", "NSC", "CP",
            # ── Energy ──
            "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "PSX", "VLO",
            "PXD", "FANG", "DVN", "HES", "HAL", "BKR",
            "KMI", "WMB", "OKE", "TRGP", "ET", "EPD", "MMP", "PAA",
            "ENPH", "SEDG", "FSLR", "RUN", "NOVA", "ARRY",
            "CEG", "VST", "NRG", "OGE",
            # ── Autos / EV ──
            "GM", "F", "RIVN", "LCID", "GOEV", "FSR", "VFS", "PSNY",
            "UBER", "LYFT", "GRAB",
            "TM", "HMC", "STLA", "RACE", "TSLA",
            # ── Chinese ADRs (US-listed) ──
            "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "BILI", "TME",
            "FUTU", "TIGR", "ZH", "TAL", "EDU", "VNET", "WB", "IQ", "DIDI",
            "YMM", "KC", "MNSO", "LKNCY",
            # ── Telecom / media ──
            "T", "VZ", "TMUS", "CHTR", "LBRDA", "FYBR",
            # ── Utilities ──
            "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ED",
            "ES", "AEE", "CMS", "DTE", "LNT", "EVRG", "PNW", "ATO", "NI",
            # ── REITs ──
            "AMT", "PLD", "CCI", "EQIX", "SPG", "O", "DLR", "PSA", "WELL", "AVB",
            "EQR", "VTR", "MAA", "UDR", "ESS", "CPT", "KIM", "REG", "FRT",
            "BXP", "VNO", "SLG", "HIW", "ARE", "PEAK", "MPW", "SBAC",
            "INVH", "AMH", "STAG", "TRNO", "REXR", "FR",
            # ── Materials / mining ──
            "LIN", "APD", "SHW", "ECL", "DD", "DOW", "PPG", "NEM",
            "FCX", "SCCO", "TECK", "CLF", "X", "NUE", "STLD", "RS",
            "AA", "CENX", "ATI", "BALL", "PKG", "IP", "WRK", "SEE",
            "CF", "MOS", "NTR", "FMC", "IPI",
            # ── Other notable US-listed ──
            "CSCO", "IBM", "ACN", "ABNB", "DASH", "DELL", "HPQ", "HPE",
            "LRCX", "NTAP", "STX", "WDC", "SMCI",
            "TWLO", "SPLK", "VEEV", "ANSS", "CDNS", "SNPS", "TYL", "MANH",
            "BSY", "GRAB", "CPNG", "SE",
        ],
        "eu": [
            # ── Germany (Xetra / DAX 40 + MDAX) ──
            "SAP", "SIE.DE", "ALV.DE", "MUV2.DE", "DTE.DE", "DHL.DE", "AIR.DE",
            "BMW.DE", "VOW3.DE", "MBG.DE", "P911.DE", "PAH3.DE",
            "BAS.DE", "BAYN.DE", "FRE.DE", "HEN3.DE", "BEI.DE",
            "ADS.DE", "PUM.DE", "ZAL.DE", "HFG.DE",
            "IFX.DE", "MRK.DE", "SRT3.DE", "RHM.DE", "MTX.DE",
            "DB1.DE", "CBK.DE", "DBK.DE",
            "RWE.DE", "EOAN.DE", "ENR.DE",
            "HEI.DE", "FME.DE", "SHL.DE", "EVK.DE", "SY1.DE",
            "LEG.DE", "1COV.DE", "WCH.DE",
            # ── France (CAC 40 + SBF 120) ──
            "MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "BNP.PA", "AI.PA", "AIR.PA",
            "SU.PA", "RI.PA", "KER.PA", "DG.PA", "HO.PA", "SGO.PA",
            "CAP.PA", "STM.PA", "DSY.PA", "BN.PA", "EN.PA", "VIV.PA",
            "ACA.PA", "GLE.PA", "CS.PA", "ML.PA", "PUB.PA",
            "ORA.PA", "EL.PA", "RMS.PA", "ERF.PA", "WLN.PA",
            "ATO.PA", "LR.PA", "SAF.PA", "AM.PA",
            # ── Netherlands (AEX) ──
            "ASML", "PHIA.AS", "UNA.AS", "INGA.AS", "AD.AS", "HEIA.AS",
            "ABN.AS", "RAND.AS", "WKL.AS", "AKZA.AS", "DSM.AS", "BESI.AS",
            "PRX.AS", "JDEP.AS", "NN.AS",
            # ── Belgium ──
            "UCB.BR", "SOLB.BR", "ABI.BR", "KBC.BR", "ACKB.BR",
            # ── Nordic (Denmark, Sweden, Finland, Norway) ──
            "NVO", "NOVO-B.CO", "CARL-B.CO", "MAERSK-B.CO", "VWS.CO", "ORSTED.CO",
            "DSV.CO", "COLO-B.CO", "PNDORA.CO", "GN.CO",
            "ERIC-B.ST", "VOLV-B.ST", "ABB.ST", "ATCO-A.ST", "SEB-A.ST",
            "INVE-B.ST", "SAND.ST", "ALFA.ST", "HM-B.ST", "SCA-B.ST",
            "ASSA-B.ST", "HEXA-B.ST", "SWED-A.ST",
            "NOKIA.HE", "SAMPO.HE", "NESTE.HE", "UPM.HE", "FORTUM.HE",
            "NHY.OL", "EQNR.OL", "DNB.OL", "TEL.OL", "MOWI.OL", "ORK.OL",
            "SALM.OL", "YAR.OL", "AKER.OL",
            # ── UK (FTSE 100 + 250) ──
            "SHEL", "AZN", "ULVR.L", "HSBA.L", "BP.L", "RIO.L", "GSK.L",
            "BARC.L", "LLOY.L", "VOD.L", "BT-A.L", "DGE.L", "LSEG.L",
            "AAL.L", "ABF.L", "AHT.L", "ANTO.L", "AUTO.L", "AVST.L",
            "AV.L", "BAT.L", "BDEV.L", "BKG.L", "BNZL.L",
            "CPG.L", "CRH.L", "DARK.L", "EXPN.L", "FLTR.L",
            "GLEN.L", "HLMA.L", "IAG.L", "III.L", "IMB.L",
            "INF.L", "ITV.L", "JD.L", "JMAT.L", "KGF.L",
            "LAND.L", "LGEN.L", "MNG.L", "NWG.L", "PHNX.L",
            "PRU.L", "PSH.L", "PSN.L", "RKT.L", "RMV.L",
            "RS1.L", "SBRY.L", "SDR.L", "SGE.L", "SHEL.L",
            "SKG.L", "SMDS.L", "SMT.L", "SN.L", "SSE.L",
            "STAN.L", "SVT.L", "TSCO.L", "TW.L", "WPP.L",
            # ── Switzerland (SMI + SPI) ──
            "NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW", "ABBN.SW", "SREN.SW",
            "CSGN.SW", "ZURN.SW", "GEBN.SW", "GIVN.SW", "SGSN.SW",
            "LONN.SW", "SCMN.SW", "SLHN.SW", "STMN.SW", "TEMN.SW",
            "BAER.SW", "BARN.SW",
            # ── Spain (IBEX 35) ──
            "SAN", "BBVA", "ITX.MC", "TEF.MC", "IBE.MC", "REP.MC", "FER.MC",
            "AMS.MC", "CABK.MC", "MAP.MC", "ACS.MC", "ENG.MC",
            "IAG.MC", "GRF.MC", "CLNX.MC", "MTS.MC",
            # ── Italy (FTSE MIB) ──
            "UCG.MI", "ISP.MI", "ENI.MI", "ENEL.MI", "RACE.MI",
            "STM.MI", "G.MI", "TEN.MI", "PRY.MI", "BAMI.MI",
            "STLA.MI", "A2A.MI", "SRG.MI", "HER.MI", "LDO.MI",
            # ── Portugal / Ireland / other ──
            "EDP.LS", "GALP.LS", "SON.LS",
            "CRH", "RYA.IR", "KYGA.IR",
            # ── European ETFs (US-listed) ──
            "EWG", "EWU", "EWQ", "EWP", "EWI", "EWL", "EWN", "EWD",
            "FEZ", "VGK", "HEDJ", "IEV", "EZU",
        ],
        "asia": [
            # ── Japan (Nikkei 225 / TOPIX) ──
            "TM", "SONY", "HMC", "NTDOY", "MUFG", "SMFG", "NMR",
            "7203.T", "6758.T", "9984.T", "8306.T", "6861.T", "6501.T",
            "7267.T", "6902.T", "8035.T", "6098.T", "4063.T", "9433.T",
            "7741.T", "4519.T", "4502.T", "6367.T", "8058.T", "8001.T",
            "9432.T", "7974.T", "4661.T", "6594.T", "6981.T",
            "8316.T", "8411.T", "3382.T", "9983.T", "7011.T", "6301.T",
            "2914.T", "8031.T", "4543.T", "4568.T", "6723.T",
            # ── China / Hong Kong (Hang Seng + ADRs) ──
            "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "BILI", "TME",
            "9988.HK", "0700.HK", "3690.HK", "1211.HK", "0941.HK", "1299.HK", "2318.HK",
            "0005.HK", "0388.HK", "0016.HK", "0001.HK", "0003.HK", "0027.HK",
            "2020.HK", "9618.HK", "9999.HK", "1810.HK", "2269.HK", "6862.HK",
            "0175.HK", "0883.HK", "2628.HK", "1398.HK", "3988.HK", "0939.HK",
            "600519.SS", "601318.SS", "601012.SS", "600036.SS", "000858.SZ",
            "000333.SZ", "300750.SZ", "002594.SZ", "600900.SS",
            # ── Taiwan ──
            "TSM", "2330.TW", "2317.TW", "2454.TW", "2412.TW", "2308.TW",
            "3711.TW", "2881.TW", "2882.TW", "2886.TW",
            # ── South Korea ──
            "005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS",
            "035720.KS", "068270.KS", "055550.KS", "105560.KS", "003550.KS",
            # ── India (NSE / ADRs) ──
            "INFY", "WIT", "HDB", "IBN", "SIFY", "RDY", "TTM",
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
            "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TATAMOTORS.NS",
            "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "NESTLEIND.NS", "HCLTECH.NS",
            "ADANIENT.NS", "ADANIPORTS.NS", "ADANIGREEN.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
            # ── Southeast Asia ──
            "SE", "GRAB", "GOTO.JK",
            "DBS.SI", "OCBC.SI", "UOB.SI", "SGX.SI",
            "BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK",
            "BDO.PS", "SM.PS", "ALI.PS", "JFC.PS",
            "PTT.BK", "SCC.BK", "AOT.BK", "CPALL.BK",
            "MAYBANK.KL", "PBBANK.KL", "TENAGA.KL", "PCHEM.KL",
            # ── Australia (ASX 200) ──
            "BHP", "CBA.AX", "CSL.AX", "WDS.AX", "NAB.AX",
            "ANZ.AX", "WBC.AX", "MQG.AX", "FMG.AX", "WES.AX",
            "TLS.AX", "RIO.AX", "NCM.AX", "ALL.AX", "WOW.AX",
            "REA.AX", "GMG.AX", "TCL.AX", "COL.AX", "SHL.AX",
            # ── New Zealand ──
            "FPH.NZ", "SPK.NZ", "ATM.NZ",
            # ── Asia ETFs (US-listed) ──
            "EWJ", "EWT", "EWY", "EWH", "EWS", "EWA", "EWZ",
            "FXI", "KWEB", "CQQQ", "INDA", "INDY", "PIN", "EPI",
            "VPL", "AAXJ", "ASHR", "MCHI",
        ],
        "latam": [
            # ── Brazil (Ibovespa / ADRs) ──
            "VALE", "PBR", "PBR-A", "ITUB", "BBD", "ABEV", "NU", "XP", "PAGS", "STNE",
            "ERJ", "BRFS", "CIG", "CBD", "SBS", "UGP", "GGB", "SID", "BSBR",
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "B3SA3.SA", "WEGE3.SA",
            "ABEV3.SA", "BBAS3.SA", "RENT3.SA", "EQTL3.SA", "RAIL3.SA", "SUZB3.SA",
            "MGLU3.SA", "VBBR3.SA", "CSNA3.SA", "GGBR4.SA", "GOAU4.SA", "USIM5.SA",
            "CYRE3.SA", "MRVE3.SA", "COGN3.SA", "NTCO3.SA", "TOTS3.SA", "RADL3.SA",
            "HAPV3.SA", "BEEF3.SA", "JBSS3.SA", "MRFG3.SA", "CPLE6.SA", "ENBR3.SA",
            # ── Argentina (Merval / ADRs) ──
            "MELI", "GLOB", "LOMA", "YPF", "GGAL", "BMA", "CRESY", "PAM", "TEO", "SUPV",
            "CEPU", "EDN", "TGS", "IRCP", "DESP",
            # ── Mexico (BMV / ADRs) ──
            "AMX", "FEMSA", "BSMX", "KOF", "OMAB", "ASUR", "PAC", "TV",
            "WALMEX.MX", "GFNORTEO.MX", "CEMEXCPO.MX", "FEMSAUBD.MX", "AMXB.MX",
            "AC.MX", "BIMBOA.MX", "GCARSOA1.MX", "GMEXICOB.MX", "GAPB.MX",
            "LIVEPOLC-1.MX", "PE&OLES.MX", "ORBIA.MX", "GRUMAB.MX",
            # ── Chile (IPSA / ADRs) ──
            "SQM", "BSAC", "LTM", "CCU", "ENELCHILE", "ECL.SN",
            "CENCOSUD.SN", "FALABELLA.SN", "BCI.SN", "CMPC.SN", "COPEC.SN", "CAP.SN",
            # ── Colombia (BVC / ADRs) ──
            "EC", "COPA", "CIB", "AVAL",
            "PFBCOLOM.BVC", "ECOPETL.BVC", "ISA.BVC", "GRUPOARGOS.BVC",
            # ── Peru ──
            "BVN", "SUZ", "BAP", "IFS",
            # ── Other LATAM ──
            "ARCO", "VIVO", "LREN3.SA",
            # ── LATAM ETFs (US-listed) ──
            "EWZ", "EWW", "ECH", "ILF", "GXG", "EPU", "ARGT", "FLBR",
        ],
        "crypto": [
            # ── Major / Layer 1 ──
            "BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "MATIC", "ATOM",
            "XRP", "BNB", "TRX", "TON", "NEAR", "SUI", "APT", "SEI", "INJ",
            "FTM", "ALGO", "HBAR", "ICP", "FIL", "EGLD", "FLOW",
            # ── DeFi ──
            "LINK", "UNI", "AAVE", "MKR", "LDO", "CRV", "SNX", "COMP",
            "SUSHI", "DYDX", "GMX", "PENDLE", "JUP", "RAY",
            # ── Layer 2 / Infrastructure ──
            "ARB", "OP", "STRK", "IMX", "RNDR", "GRT", "FET", "AGIX",
            "THETA", "AR", "OCEAN", "AKT",
            # ── Other major ──
            "LTC", "BCH", "ETC", "XLM", "VET", "SAND", "MANA", "AXS",
            "ENJ", "GALA", "APE", "BLUR", "CRO", "OKB", "LEO",
            # ── Memecoins ──
            "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "TRUMP",
            "MEME", "MYRO", "POPCAT", "BRETT", "MOG", "SPX", "TURBO", "NEIRO",
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

    data = await market_data_service.get_extended_movers(symbols=symbols, threshold=threshold)
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

    indicators = [MacroIndicatorDetail(**m) for m in raw_indicators]

    return MacroIntelligenceResponse(
        indicators=indicators,
        summary=MacroSummary(**summary),
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
    if not news_service.is_configured:
        return {
            "configured": False,
            "symbol": symbol.upper(),
            "reddit": {"mentions": 0, "score": 0},
            "twitter": {"mentions": 0, "score": 0},
            "total_mentions": 0,
            "combined_score": 0,
            "buzz_level": "none",
            "sentiment_label": "neutral",
        }

    data = await news_service.get_social_sentiment(symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"No social sentiment data for '{symbol.upper()}'")
    data["configured"] = True
    return data


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
