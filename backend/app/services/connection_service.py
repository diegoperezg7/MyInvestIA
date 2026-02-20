"""Connection orchestrator service — manages the full lifecycle of external connections."""

import logging
import time
import uuid
from datetime import datetime, timezone

from app.services import encryption_service, exchange_service, wallet_service, etoro_service, polymarket_service
from app.services.store import store

logger = logging.getLogger(__name__)

# Supported providers with metadata
SUPPORTED_PROVIDERS = [
    # --- Exchanges (CCXT) ---
    {
        "id": "binance",
        "name": "Binance",
        "type": "exchange",
        "description": "World's largest crypto exchange by volume",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/binance.png",
    },
    {
        "id": "coinbase",
        "name": "Coinbase",
        "type": "exchange",
        "description": "US-regulated crypto exchange",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/coinbase.png",
    },
    {
        "id": "kraken",
        "name": "Kraken",
        "type": "exchange",
        "description": "Established crypto exchange with fiat pairs",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/kraken.png",
    },
    {
        "id": "kucoin",
        "name": "KuCoin",
        "type": "exchange",
        "description": "Global crypto exchange with 700+ tokens",
        "fields_required": ["api_key", "api_secret", "passphrase"],
        "logo_url": "/logos/kucoin.png",
    },
    {
        "id": "bybit",
        "name": "Bybit",
        "type": "exchange",
        "description": "Derivatives and spot crypto exchange",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/bybit.png",
    },
    {
        "id": "okx",
        "name": "OKX",
        "type": "exchange",
        "description": "Global crypto exchange with Web3 wallet",
        "fields_required": ["api_key", "api_secret", "passphrase"],
        "logo_url": "/logos/okx.png",
    },
    {
        "id": "gateio",
        "name": "Gate.io",
        "type": "exchange",
        "description": "Crypto exchange with 1,700+ tokens",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/gateio.png",
    },
    {
        "id": "bitfinex",
        "name": "Bitfinex",
        "type": "exchange",
        "description": "Advanced crypto trading platform",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/bitfinex.png",
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "type": "exchange",
        "description": "US-regulated crypto exchange by Winklevoss",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/gemini.png",
    },
    {
        "id": "cryptocom",
        "name": "Crypto.com",
        "type": "exchange",
        "description": "Crypto exchange with Visa card and DeFi wallet",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/cryptocom.png",
    },
    {
        "id": "htx",
        "name": "HTX (Huobi)",
        "type": "exchange",
        "description": "Global crypto exchange (formerly Huobi)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/htx.png",
    },
    {
        "id": "bitget",
        "name": "Bitget",
        "type": "exchange",
        "description": "Crypto exchange with copy-trading features",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/bitget.png",
    },
    {
        "id": "mexc",
        "name": "MEXC",
        "type": "exchange",
        "description": "Crypto exchange with 1,500+ trading pairs",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/mexc.png",
    },
    # --- Wallets ---
    {
        "id": "metamask",
        "name": "MetaMask",
        "type": "wallet",
        "description": "EVM wallet — track any Ethereum, Polygon, BSC address",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/metamask.png",
    },
    {
        "id": "trustwallet",
        "name": "Trust Wallet",
        "type": "wallet",
        "description": "Multi-chain crypto wallet by Binance",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/trustwallet.png",
    },
    {
        "id": "coinbase_wallet",
        "name": "Coinbase Wallet",
        "type": "wallet",
        "description": "Self-custody EVM wallet by Coinbase",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/coinbase_wallet.png",
    },
    {
        "id": "ledger",
        "name": "Ledger",
        "type": "wallet",
        "description": "Hardware wallet — track your Ledger addresses",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/ledger.png",
    },
    {
        "id": "rainbow",
        "name": "Rainbow",
        "type": "wallet",
        "description": "Ethereum & L2 wallet with beautiful UI",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/rainbow.png",
    },
    {
        "id": "phantom",
        "name": "Phantom",
        "type": "wallet",
        "description": "Solana & multi-chain wallet (Solana support coming soon)",
        "fields_required": ["address", "chain"],
        "logo_url": "/logos/phantom.png",
    },
    # --- Brokers ---
    {
        "id": "etoro",
        "name": "eToro",
        "type": "broker",
        "description": "Social trading platform — stocks, crypto, ETFs (API access limited)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/etoro.png",
    },
    {
        "id": "ibkr",
        "name": "Interactive Brokers",
        "type": "broker",
        "description": "Professional trading platform — complex OAuth required",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/ibkr.png",
    },
    {
        "id": "robinhood",
        "name": "Robinhood",
        "type": "broker",
        "description": "Commission-free stock & crypto trading (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/robinhood.png",
    },
    {
        "id": "trading212",
        "name": "Trading 212",
        "type": "broker",
        "description": "Commission-free stocks & ETFs (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/trading212.png",
    },
    {
        "id": "degiro",
        "name": "DEGIRO",
        "type": "broker",
        "description": "Low-cost European broker (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/degiro.png",
    },
    {
        "id": "xtb",
        "name": "XTB",
        "type": "broker",
        "description": "European CFD & stock broker (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/xtb.png",
    },
    {
        "id": "revolut",
        "name": "Revolut",
        "type": "broker",
        "description": "Digital bank with stock & crypto trading (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/revolut.png",
    },
    {
        "id": "plus500",
        "name": "Plus500",
        "type": "broker",
        "description": "CFD trading platform (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/plus500.png",
    },
    {
        "id": "schwab",
        "name": "Charles Schwab",
        "type": "broker",
        "description": "US brokerage (formerly TD Ameritrade) — API available",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/schwab.png",
    },
    {
        "id": "fidelity",
        "name": "Fidelity",
        "type": "broker",
        "description": "US brokerage & investment management (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/fidelity.png",
    },
    {
        "id": "n26",
        "name": "N26",
        "type": "broker",
        "description": "European digital bank with stocks & ETFs (no public API)",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/n26.png",
    },
    # --- Prediction Markets ---
    {
        "id": "polymarket",
        "name": "Polymarket",
        "type": "prediction",
        "description": "Prediction market — track positions on event outcomes",
        "fields_required": ["wallet_address"],
        "logo_url": "/logos/polymarket.png",
    },
    {
        "id": "kalshi",
        "name": "Kalshi",
        "type": "prediction",
        "description": "US-regulated prediction market with REST API",
        "fields_required": ["api_key", "api_secret"],
        "logo_url": "/logos/kalshi.png",
    },
]


def get_providers() -> list[dict]:
    """Return list of supported providers."""
    return SUPPORTED_PROVIDERS


def list_connections(user_id: str) -> list[dict]:
    """List all connections with summary info."""
    connections = store.get_connections(user_id)
    result = []
    for conn in connections:
        holdings = store.get_holdings_by_connection(user_id, conn["id"])
        total_value = sum(h.get("quantity", 0) * h.get("avg_buy_price", 0) for h in holdings)
        result.append({
            **conn,
            "holdings_count": len(holdings),
            "total_value": round(total_value, 2),
        })
    return result


def get_connection(user_id: str, connection_id: str) -> dict | None:
    """Get connection detail with holdings."""
    conn = store.get_connection(user_id, connection_id)
    if not conn:
        return None
    holdings = store.get_holdings_by_connection(user_id, connection_id)
    total_value = sum(h.get("quantity", 0) * h.get("avg_buy_price", 0) for h in holdings)
    return {
        **conn,
        "holdings_count": len(holdings),
        "total_value": round(total_value, 2),
        "holdings": holdings,
    }


def create_exchange_connection(
    user_id: str, provider: str, label: str, api_key: str, api_secret: str, passphrase: str | None = None
) -> dict:
    """Create and test an exchange connection."""
    # Encrypt credentials
    creds = {"api_key": api_key, "api_secret": api_secret}
    if passphrase:
        creds["passphrase"] = passphrase
    encrypted = encryption_service.encrypt(creds)

    # Test before saving
    test = exchange_service.test_connection(provider, creds)
    status = "active" if test["success"] else "error"

    conn = store.create_connection(user_id, {
        "id": str(uuid.uuid4()),
        "type": "exchange",
        "provider": provider,
        "label": label,
        "status": status,
        "credentials_encrypted": encrypted,
        "wallet_address": None,
        "chain": None,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_error": test.get("message") if not test["success"] else None,
        "sync_count": 0,
        "metadata": test.get("account_info", {}),
    })
    return {**conn, "holdings_count": 0, "total_value": 0.0, "test_result": test}


async def create_wallet_connection(user_id: str, label: str, address: str, chain: str, provider: str = "metamask") -> dict:
    """Create a wallet connection (no encryption needed — address is public)."""
    # Phantom/Solana not yet supported for balance fetching
    if provider == "phantom" and chain == "solana":
        conn = store.create_connection(user_id, {
            "id": str(uuid.uuid4()),
            "type": "wallet",
            "provider": provider,
            "label": label,
            "status": "pending",
            "credentials_encrypted": None,
            "wallet_address": address,
            "chain": chain,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_error": "Solana balance tracking coming soon",
            "sync_count": 0,
            "metadata": {"chain": chain},
        })
        return {**conn, "holdings_count": 0, "total_value": 0.0}

    if not wallet_service.validate_address(address, chain):
        raise ValueError(f"Invalid wallet address format for chain {chain}")

    conn = store.create_connection(user_id, {
        "id": str(uuid.uuid4()),
        "type": "wallet",
        "provider": provider,
        "label": label,
        "status": "active",
        "credentials_encrypted": None,
        "wallet_address": address,
        "chain": chain,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_error": None,
        "sync_count": 0,
        "metadata": {"chain": chain},
    })
    return {**conn, "holdings_count": 0, "total_value": 0.0}


def create_broker_connection(user_id: str, label: str, api_key: str, api_secret: str, provider: str = "etoro") -> dict:
    """Create a broker connection. Most brokers lack public APIs so start as pending."""
    creds = {"api_key": api_key, "api_secret": api_secret}
    encrypted = encryption_service.encrypt(creds)

    # Only eToro has a test_connection implementation; others start as pending
    if provider == "etoro":
        test = etoro_service.test_connection(creds)
        status = "active" if test["success"] else "pending"
    else:
        test = {"success": False, "message": f"{provider} API integration pending — credentials saved", "account_info": {}}
        status = "pending"

    conn = store.create_connection(user_id, {
        "id": str(uuid.uuid4()),
        "type": "broker",
        "provider": provider,
        "label": label,
        "status": status,
        "credentials_encrypted": encrypted,
        "wallet_address": None,
        "chain": None,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_error": test.get("message") if not test["success"] else None,
        "sync_count": 0,
        "metadata": test.get("account_info", {}),
    })
    return {**conn, "holdings_count": 0, "total_value": 0.0, "test_result": test}


def create_prediction_connection(
    user_id: str, label: str, provider: str = "polymarket", api_key: str | None = None, wallet_address: str | None = None
) -> dict:
    """Create a prediction market connection (Polymarket, Kalshi)."""
    creds = {}
    if api_key:
        creds["api_key"] = api_key
    if wallet_address:
        creds["wallet_address"] = wallet_address

    if provider == "polymarket":
        test = polymarket_service.test_connection(creds)
        status = "active" if test["success"] else "error"
    else:
        # Kalshi and future prediction markets start as pending
        test = {"success": False, "message": f"{provider} API integration pending — credentials saved", "account_info": {}}
        status = "pending"

    encrypted = encryption_service.encrypt(creds) if api_key else None

    conn = store.create_connection(user_id, {
        "id": str(uuid.uuid4()),
        "type": "prediction",
        "provider": provider,
        "label": label,
        "status": status,
        "credentials_encrypted": encrypted,
        "wallet_address": wallet_address,
        "chain": "polygon" if provider == "polymarket" else None,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_error": test.get("message") if not test["success"] else None,
        "sync_count": 0,
        "metadata": test.get("account_info", {}),
    })
    return {**conn, "holdings_count": 0, "total_value": 0.0, "test_result": test}


def delete_connection(user_id: str, connection_id: str) -> bool:
    """Delete a connection and all its synced holdings."""
    conn = store.get_connection(user_id, connection_id)
    if not conn:
        return False
    store.delete_holdings_by_connection(user_id, connection_id)
    return store.delete_connection(user_id, connection_id)


async def sync_connection(user_id: str, connection_id: str) -> dict:
    """Sync a single connection: fetch balances and upsert holdings."""
    conn = store.get_connection(user_id, connection_id)
    if not conn:
        raise ValueError(f"Connection {connection_id} not found")

    if conn["status"] not in ("active", "error"):
        raise ValueError(f"Connection {connection_id} is {conn['status']} — cannot sync")

    start = time.time()
    sync_record = {
        "id": str(uuid.uuid4()),
        "connection_id": connection_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }
    store.add_sync_history(user_id, sync_record)

    try:
        # Fetch balances from the appropriate service
        balances = await _fetch_balances(conn)

        # Get existing synced holdings for this connection
        existing = store.get_holdings_by_connection(user_id, connection_id)
        existing_symbols = {h["symbol"] for h in existing}
        new_symbols = {b["symbol"] for b in balances}

        added = 0
        updated = 0
        removed = 0

        # Upsert holdings
        for b in balances:
            if b["symbol"] in existing_symbols:
                updated += 1
            else:
                added += 1
            store.upsert_synced_holding(
                user_id,
                symbol=b["symbol"],
                name=b["name"],
                asset_type=b["type"],
                quantity=b["quantity"],
                avg_buy_price=b["avg_buy_price"],
                source=conn["type"],
                connection_id=connection_id,
            )

        # Remove holdings no longer in source
        for h in existing:
            if h["symbol"] not in new_symbols:
                store.delete_synced_holding(user_id, h["symbol"], connection_id)
                removed += 1

        duration_ms = int((time.time() - start) * 1000)
        now = datetime.now(timezone.utc).isoformat()

        # Update sync history
        sync_record.update({
            "completed_at": now,
            "status": "success",
            "holdings_synced": len(balances),
            "holdings_added": added,
            "holdings_updated": updated,
            "holdings_removed": removed,
        })
        store.update_sync_history(user_id, sync_record["id"], sync_record)

        # Update connection
        store.update_connection(user_id, connection_id, {
            "last_sync_at": now,
            "last_sync_status": "success",
            "last_sync_error": None,
            "sync_count": conn.get("sync_count", 0) + 1,
            "status": "active",
        })

        return {
            "connection_id": connection_id,
            "status": "success",
            "holdings_synced": len(balances),
            "holdings_added": added,
            "holdings_updated": updated,
            "holdings_removed": removed,
            "duration_ms": duration_ms,
            "error": None,
        }

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        now = datetime.now(timezone.utc).isoformat()
        error_msg = str(e)

        sync_record.update({
            "completed_at": now,
            "status": "failed",
            "error_message": error_msg,
        })
        store.update_sync_history(user_id, sync_record["id"], sync_record)

        store.update_connection(user_id, connection_id, {
            "last_sync_at": now,
            "last_sync_status": "failed",
            "last_sync_error": error_msg,
            "status": "error",
        })

        return {
            "connection_id": connection_id,
            "status": "failed",
            "holdings_synced": 0,
            "holdings_added": 0,
            "holdings_updated": 0,
            "holdings_removed": 0,
            "duration_ms": duration_ms,
            "error": error_msg,
        }


async def sync_all(user_id: str) -> list[dict]:
    """Sync all active connections."""
    connections = store.get_connections(user_id)
    results = []
    for conn in connections:
        if conn["status"] in ("active", "error"):
            result = await sync_connection(user_id, conn["id"])
            results.append(result)
    return results


async def test_connection_by_id(user_id: str, connection_id: str) -> dict:
    """Test an existing connection's credentials."""
    conn = store.get_connection(user_id, connection_id)
    if not conn:
        raise ValueError(f"Connection {connection_id} not found")

    conn_type = conn["type"]

    if conn_type == "exchange":
        creds = encryption_service.decrypt(conn["credentials_encrypted"])
        return exchange_service.test_connection(conn["provider"], creds)
    elif conn_type == "wallet":
        valid = wallet_service.validate_address(conn["wallet_address"], conn.get("chain", "ethereum"))
        return {
            "success": valid,
            "message": "Wallet address is valid" if valid else "Invalid wallet address",
            "account_info": {"address": conn["wallet_address"], "chain": conn.get("chain")},
        }
    elif conn_type == "broker":
        creds = encryption_service.decrypt(conn["credentials_encrypted"])
        return etoro_service.test_connection(creds)
    elif conn_type == "prediction":
        creds = {}
        if conn.get("wallet_address"):
            creds["wallet_address"] = conn["wallet_address"]
        if conn.get("credentials_encrypted"):
            creds.update(encryption_service.decrypt(conn["credentials_encrypted"]))
        return polymarket_service.test_connection(creds)

    return {"success": False, "message": f"Unknown connection type: {conn_type}", "account_info": {}}


def get_sync_history(user_id: str, connection_id: str, limit: int = 20) -> list[dict]:
    """Get sync history for a connection."""
    return store.get_sync_history(user_id, connection_id, limit)


async def _fetch_balances(conn: dict) -> list[dict]:
    """Fetch balances from the appropriate service based on connection type."""
    conn_type = conn["type"]

    if conn_type == "exchange":
        return exchange_service.fetch_balances(conn["provider"], conn["credentials_encrypted"])
    elif conn_type == "wallet":
        return await wallet_service.fetch_balances(conn["wallet_address"], conn.get("chain", "ethereum"))
    elif conn_type == "broker":
        return await etoro_service.fetch_portfolio(conn["credentials_encrypted"])
    elif conn_type == "prediction":
        address = conn.get("wallet_address")
        api_key = None
        if conn.get("credentials_encrypted"):
            creds = encryption_service.decrypt(conn["credentials_encrypted"])
            api_key = creds.get("api_key")
        return await polymarket_service.fetch_positions(wallet_address=address, api_key=api_key)

    raise ValueError(f"Unknown connection type: {conn_type}")
