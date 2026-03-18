from typing import Any, Dict, Optional

from .base import _df_to_dict, _ticker


class ChartAPI:
    """Historical OHLCV price data."""

    def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        prepost: bool = False,
        actions: bool = True,
    ) -> Dict[str, Any]:
        """Get historical price data for a symbol.

        Args:
            symbol: Ticker symbol (e.g. "AAPL").
            period: Time period to download.
                Valid: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max".
            interval: Data interval.
                Valid: "1m", "2m", "5m", "15m", "30m", "60m", "90m",
                "1h", "1d", "5d", "1wk", "1mo", "3mo".
            start: Start date string (YYYY-MM-DD). Overrides period if set.
            end: End date string (YYYY-MM-DD).
            prepost: Include pre/post market data.
            actions: Include dividends and stock splits.

        Returns:
            List of dicts with OHLCV data per row.
        """
        t = _ticker(symbol)
        kwargs = {"interval": interval, "prepost": prepost, "actions": actions}
        if start:
            kwargs["start"] = start
            if end:
                kwargs["end"] = end
        else:
            kwargs["period"] = period
        df = t.history(**kwargs)
        return _df_to_dict(df)
