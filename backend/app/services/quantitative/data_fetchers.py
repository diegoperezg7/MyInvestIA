import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class BinanceFetcher:
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.base_url = "https://api.binance.com"
        self.api_key = api_key
        self.secret_key = secret_key
        self.logger = logging.getLogger("binance_fetcher")

    def get_current_price(self, symbol: str) -> float:
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            params = {"symbol": symbol.upper()}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data["price"])
        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": limit,
            }
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            df = pd.DataFrame(
                data,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_volume",
                    "trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )

            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            return df[
                ["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]
            ]
        except Exception as e:
            self.logger.error(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()

    def get_ticker_24h(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if symbol:
                return data
            return data[:100]
        except Exception as e:
            self.logger.error(f"Error fetching 24h ticker: {e}")
            return {}

    def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/api/v3/depth"
            params = {"symbol": symbol.upper(), "limit": limit}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching order book for {symbol}: {e}")
            return {}

    def get_exchange_info(self) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/api/v3/exchangeInfo"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching exchange info: {e}")
            return {}


class AlphaVantageFetcher:
    def __init__(self, api_key: str):
        self.base_url = "https://www.alphavantage.co/query"
        self.api_key = api_key
        self.logger = logging.getLogger("alpha_vantage_fetcher")

    def get_time_series_daily(
        self, symbol: str, output_size: str = "compact"
    ) -> pd.DataFrame:
        try:
            url = self.base_url
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol.upper(),
                "outputsize": output_size,
                "apikey": self.api_key,
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "Time Series (Daily)" not in data:
                self.logger.warning(f"No data for {symbol}")
                return pd.DataFrame()

            time_series = data["Time Series (Daily)"]

            records = []
            for date, values in time_series.items():
                records.append(
                    {
                        "timestamp": pd.to_datetime(date),
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": int(values["5. volume"]),
                    }
                )

            df = pd.DataFrame(records)
            df = df.sort_values("timestamp")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching daily time series for {symbol}: {e}")
            return pd.DataFrame()

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        try:
            url = self.base_url
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol.upper(),
                "apikey": self.api_key,
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                return {
                    "symbol": quote.get("01. symbol", ""),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": float(
                        quote.get("10. change percent", "0").replace("%", "")
                    ),
                    "volume": int(quote.get("06. volume", 0)),
                    "high": float(quote.get("03. high", 0)),
                    "low": float(quote.get("04. low", 0)),
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error fetching quote for {symbol}: {e}")
            return {}

    def get_technical_indicator(
        self, symbol: str, indicator: str = "RSI", period: int = 14
    ) -> pd.DataFrame:
        try:
            url = self.base_url
            params = {
                "function": indicator,
                "symbol": symbol.upper(),
                "interval": "daily",
                "time_period": period,
                "apikey": self.api_key,
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            indicator_key = f"Technical Analysis: {indicator}"
            if indicator_key not in data:
                return pd.DataFrame()

            records = []
            for date, values in data[indicator_key].items():
                record = {"timestamp": pd.to_datetime(date)}
                for key, value in values.items():
                    record[key.lower()] = float(value)
                records.append(record)

            df = pd.DataFrame(records)
            df = df.sort_values("timestamp")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching {indicator} for {symbol}: {e}")
            return pd.DataFrame()


class YahooFetcher:
    def __init__(self):
        self.logger = logging.getLogger("yahoo_fetcher")

    def get_historical(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                return pd.DataFrame()

            df = data.reset_index()
            if "Date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["Date"])
            elif "Datetime" in df.columns:
                df["timestamp"] = pd.to_datetime(df["Datetime"])

            df["open"] = df["Open"].astype(float)
            df["high"] = df["High"].astype(float)
            df["low"] = df["Low"].astype(float)
            df["close"] = df["Close"].astype(float)
            df["volume"] = df["Volume"].astype(int)

            return df[["timestamp", "open", "high", "low", "close", "volume"]]
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "change": info.get("regularMarketChange", 0),
                "change_percent": info.get("regularMarketChangePercent", 0),
                "volume": info.get("regularMarketVolume", 0),
                "high": info.get("regularMarketDayHigh", 0),
                "low": info.get("regularMarketDayLow", 0),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
            }
        except Exception as e:
            self.logger.error(f"Error fetching quote for {symbol}: {e}")
            return {}


def get_fetcher(provider: str, **kwargs) -> Any:
    fetchers = {
        "binance": BinanceFetcher,
        "alphavantage": AlphaVantageFetcher,
        "yahoo": YahooFetcher,
    }

    fetcher_class = fetchers.get(provider.lower())
    if not fetcher_class:
        raise ValueError(f"Unknown fetcher provider: {provider}")

    return fetcher_class(**kwargs)
