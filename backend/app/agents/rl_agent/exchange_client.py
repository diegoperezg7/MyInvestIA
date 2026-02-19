"""
CCXT Exchange Integration for RL Trading Agent.
Supports testnet trading on various exchanges.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import ccxt
import pandas as pd


class ExchangeClient:
    """
    Client for exchange trading via CCXT.
    Supports testnet for safe trading.
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        verbose: bool = False,
    ):
        self.exchange_id = exchange_id
        self.api_key = api_key or os.environ.get(f"{exchange_id.upper()}_API_KEY", "")
        self.api_secret = api_secret or os.environ.get(
            f"{exchange_id.upper()}_API_SECRET", ""
        )
        self.testnet = testnet
        self.verbose = verbose

        self.exchange = self._init_exchange()

    def _init_exchange(self):
        """Initialize CCXT exchange instance."""

        # Get exchange class
        exchange_class = getattr(ccxt, self.exchange_id)

        # Configure options for testnet
        options = {
            "enableRateLimit": True,
            "verbose": self.verbose,
        }

        if self.testnet:
            # Testnet configuration
            if self.exchange_id == "binance":
                options.update(
                    {
                        "urls": {
                            "api": {
                                "public": "https://testnet.binance.vision/api",
                                "private": "https://testnet.binance.vision/api",
                            }
                        }
                    }
                )
            elif self.exchange_id == "coinbase":
                options.update(
                    {
                        "urls": {
                            "api": "https://api-public.sandbox.exchange.coinbase.com",
                        }
                    }
                )

        # Create exchange instance
        if self.api_key and self.api_secret:
            exchange = exchange_class(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "enableRateLimit": True,
                    "options": options,
                }
            )
        else:
            # Public only (for fetching data)
            exchange = exchange_class(
                {
                    "enableRateLimit": True,
                    "options": options,
                }
            )

        return exchange

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Fetch OHLCV data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            return df
        except Exception as e:
            print(f"Error fetching OHLCV: {e}")
            return pd.DataFrame()

    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        try:
            if not self.api_key:
                return {"error": "No API key configured"}

            balance = await self.exchange.fetch_balance()
            return {
                "free": balance.get("free", {}),
                "used": balance.get("used", {}),
                "total": balance.get("total", {}),
            }
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {"error": str(e)}

    async def create_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        order_type: str = "market",  # 'market' or 'limit'
        amount: float = 0,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a trade order."""
        try:
            if not self.api_key:
                return {"error": "No API key configured - using paper mode"}

            if self.testnet:
                print(
                    f"[TESTNET] Would create order: {side} {amount} {symbol} @ {price or 'market'}"
                )
                return {
                    "id": f"testnet_{datetime.now().timestamp()}",
                    "status": "testnet",
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "symbol": symbol,
                    "testnet": True,
                }

            # Real order
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
            )

            return order

        except Exception as e:
            print(f"Error creating order: {e}")
            return {"error": str(e)}

    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Fetch order status."""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            print(f"Error fetching order: {e}")
            return {"error": str(e)}

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            if self.testnet:
                return {"id": order_id, "status": "testnet_cancelled"}

            result = await self.exchange.cancel_order(order_id, symbol)
            return result
        except Exception as e:
            print(f"Error cancelling order: {e}")
            return {"error": str(e)}

    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions."""
        try:
            balance = await self.fetch_balance()

            if "error" in balance:
                return []

            positions = []
            for currency, amount in balance.get("total", {}).items():
                if amount > 0 and currency != "USDT":
                    price = balance.get("free", {}).get(currency, 0)
                    positions.append(
                        {
                            "symbol": f"{currency}/USDT",
                            "amount": amount,
                            "value": amount * price,
                        }
                    )

            return positions
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information."""
        return {
            "id": self.exchange_id,
            "name": self.exchange.name,
            "testnet": self.testnet,
            "hasPublicAPI": True,
            "hasPrivateAPI": bool(self.api_key),
            "features": list(self.exchange.has.keys()),
        }


# Supported exchanges
SUPPORTED_EXCHANGES = {
    "binance": {
        "name": "Binance",
        "testnet_url": "https://testnet.binance.vision",
        "fees": 0.001,  # 0.1%
    },
    "coinbase": {
        "name": "Coinbase",
        "testnet_url": "https://api-public.sandbox.exchange.coinbase.com",
        "fees": 0.006,  # 0.6%
    },
    "kraken": {
        "name": "Kraken",
        "testnet_url": None,
        "fees": 0.002,  # 0.2%
    },
    "kucoin": {
        "name": "KuCoin",
        "testnet_url": "https://api-sandbox.kucoin.com",
        "fees": 0.001,  # 0.1%
    },
}


def create_exchange_client(
    exchange_id: str = "binance",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    testnet: bool = True,
) -> ExchangeClient:
    """Factory function to create exchange client."""

    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {exchange_id}")

    return ExchangeClient(
        exchange_id=exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
    )


# Example usage
if __name__ == "__main__":
    import sys

    async def main():
        # Create client
        client = create_exchange_client("binance", testnet=True)

        # Print info
        print("Exchange Info:", client.get_exchange_info())

        # Fetch BTC price
        df = await client.fetch_ohlcv("BTC/USDT", "1h", 10)
        print("\nBTC/USDT OHLCV:")
        print(df.tail())

        # Fetch balance (will fail without API key)
        balance = await client.fetch_balance()
        print("\nBalance:", balance)

    asyncio.run(main())
