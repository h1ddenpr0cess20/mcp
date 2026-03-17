from typing import Any, Dict, List

from .base import _ticker


class NewsAPI:
    """News articles for a symbol."""

    def get_news(self, symbol: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent news articles for a symbol.

        Args:
            symbol: Ticker symbol.
            count: Number of articles to return (default 10).

        Returns:
            List of news article dicts with title, link, publisher, etc.
        """
        return _ticker(symbol).get_news(count=count)
