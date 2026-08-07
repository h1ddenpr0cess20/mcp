from typing import Any, Dict

import yfinance as yf

from .base import _ticker


class QuoteAPI:
    """Real-time quote, info, and market data."""

    def get_info(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive info for a symbol (price, fundamentals, profile, etc.).

        Args:
            symbol: Ticker symbol (e.g. "AAPL").

        Returns:
            Dict with all available info fields.
        """
        return _ticker(symbol).get_info()

    def get_fast_info(self, symbol: str) -> Dict[str, Any]:
        """Get a small subset of info that loads faster (price, market cap, volume).

        Args:
            symbol: Ticker symbol.

        Returns:
            Dict with fast-loading info fields.
        """
        fi = _ticker(symbol).get_fast_info()
        return dict(fi)

    def get_market_summary(self, market: str = "us_market") -> Dict[str, Any]:
        """Get a summary of major market indices.

        Args:
            market: Market identifier (e.g. "us_market", "gb_market").

        Returns:
            Dict mapping exchange codes to index data.
        """
        m = yf.Market(market)
        return m.summary

    def get_market_status(self, market: str = "us_market") -> Dict[str, Any]:
        """Get current market open/close status.

        Args:
            market: Market identifier (e.g. "us_market", "gb_market").

        Returns:
            Dict with market status including open/close times and timezone.
        """
        m = yf.Market(market)
        status = m.status
        # Convert datetime objects to strings for JSON serialization
        result = {}
        for k, v in status.items():
            try:
                result[k] = str(v)
            except Exception:
                result[k] = v
        return result
