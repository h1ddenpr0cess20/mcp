from typing import Any, Dict

import yfinance as yf


class SearchAPI:
    """Symbol search."""

    def search(
        self,
        query: str,
        max_results: int = 8,
        news_count: int = 8,
    ) -> Dict[str, Any]:
        """Search for symbols, companies, ETFs, indices, etc.

        Args:
            query: Search term (e.g. "Apple", "AAPL", "S&P 500").
            max_results: Max number of quote results.
            news_count: Max number of news results.

        Returns:
            Dict with "quotes" and "news" lists.
        """
        s = yf.Search(query, max_results=max_results, news_count=news_count)
        return {"quotes": s.quotes, "news": s.news}
