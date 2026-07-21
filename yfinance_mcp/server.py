from typing import Optional

from fastmcp import FastMCP

from yfinance_client import (
    ChartAPI,
    NewsAPI,
    OptionsAPI,
    QuoteAPI,
    SearchAPI,
    SummaryAPI,
)

mcp = FastMCP("yfinance")

_quote = QuoteAPI()
_chart = ChartAPI()
_search = SearchAPI()
_summary = SummaryAPI()
_options = OptionsAPI()
_news = NewsAPI()


# -------- Quote tools --------
@mcp.tool(description="Get comprehensive info for a symbol (price, fundamentals, profile)")
def get_info(symbol: str):
    """Get comprehensive info for a symbol.

    Args:
        symbol: Ticker symbol (e.g. "AAPL").

    Returns:
        Dict with all available info fields.
    """
    return _quote.get_info(symbol)


@mcp.tool(description="Get fast-loading price/volume snapshot for a symbol")
def get_fast_info(symbol: str):
    """Get a small subset of info that loads faster (price, market cap, volume).

    Args:
        symbol: Ticker symbol.

    Returns:
        Dict with fast-loading info fields.
    """
    return _quote.get_fast_info(symbol)


@mcp.tool(description="Get a summary of major market indices")
def get_market_summary(market: str = "us_market"):
    """Get a summary of major market indices.

    Args:
        market: Market identifier (e.g. "us_market", "gb_market").

    Returns:
        Dict mapping exchange codes to index data.
    """
    return _quote.get_market_summary(market)


@mcp.tool(description="Get current market open/close status")
def get_market_status(market: str = "us_market"):
    """Get current market open/close status.

    Args:
        market: Market identifier (e.g. "us_market", "gb_market").

    Returns:
        Dict with market status including open/close times.
    """
    return _quote.get_market_status(market)


# -------- Chart tools --------
@mcp.tool(description="Get historical OHLCV price data for a symbol")
def get_history(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    prepost: bool = False,
    actions: bool = True,
):
    """Get historical price data for a symbol.

    Args:
        symbol: Ticker symbol (e.g. "AAPL").
        period: Time period. Valid: "1d", "5d", "1mo", "3mo", "6mo",
            "1y", "2y", "5y", "10y", "ytd", "max".
        interval: Data interval. Valid: "1m", "2m", "5m", "15m", "30m",
            "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo".
        start: Start date (YYYY-MM-DD). Overrides period if set.
        end: End date (YYYY-MM-DD).
        prepost: Include pre/post market data.
        actions: Include dividends and stock splits.

    Returns:
        List of dicts with OHLCV data per row.
    """
    return _chart.get_history(symbol, period, interval, start, end, prepost, actions)


# -------- Search tools --------
@mcp.tool(description="Search for symbols, companies, ETFs, indices, etc.")
def search(
    query: str,
    max_results: int = 8,
    news_count: int = 8,
):
    """Search for symbols, companies, ETFs, indices, etc.

    Args:
        query: Search term (e.g. "Apple", "AAPL", "S&P 500").
        max_results: Max number of quote results.
        news_count: Max number of news results.

    Returns:
        Dict with "quotes" and "news" lists.
    """
    return _search.search(query, max_results, news_count)


# -------- Summary / Fundamentals tools --------
@mcp.tool(description="Get company profile — sector, industry, description, officers")
def get_profile(symbol: str):
    """Get company profile.

    Args:
        symbol: Ticker symbol.

    Returns:
        Dict with company profile.
    """
    return _summary.get_profile(symbol)


@mcp.tool(description="Get income statement (yearly or quarterly)")
def get_financials(symbol: str, freq: str = "yearly"):
    """Get income statement.

    Args:
        symbol: Ticker symbol.
        freq: "yearly" or "quarterly".

    Returns:
        Income statement records.
    """
    return _summary.get_financials(symbol, freq)


@mcp.tool(description="Get balance sheet (yearly or quarterly)")
def get_balance_sheet(symbol: str, freq: str = "yearly"):
    """Get balance sheet.

    Args:
        symbol: Ticker symbol.
        freq: "yearly" or "quarterly".

    Returns:
        Balance sheet records.
    """
    return _summary.get_balance_sheet(symbol, freq)


@mcp.tool(description="Get earnings data (yearly or quarterly)")
def get_earnings(symbol: str, freq: str = "yearly"):
    """Get earnings data.

    Args:
        symbol: Ticker symbol.
        freq: "yearly" or "quarterly".

    Returns:
        Earnings records.
    """
    return _summary.get_earnings(symbol, freq)


@mcp.tool(description="Get analyst price targets — low, current, mean, median, high")
def get_analyst_price_targets(symbol: str):
    """Get analyst price targets.

    Args:
        symbol: Ticker symbol.

    Returns:
        Dict with analyst price target data.
    """
    return _summary.get_analyst_price_targets(symbol)


@mcp.tool(description="Get analyst recommendation trends — buy, hold, sell")
def get_recommendations(symbol: str):
    """Get analyst recommendations.

    Args:
        symbol: Ticker symbol.

    Returns:
        Recommendation records.
    """
    return _summary.get_recommendations(symbol)


# -------- Options tools --------
@mcp.tool(description="Get available options expiration dates for a symbol")
def get_options_expirations(symbol: str):
    """Get available options expiration dates.

    Args:
        symbol: Ticker symbol.

    Returns:
        List of expiration date strings (YYYY-MM-DD).
    """
    return _options.get_options_expirations(symbol)


@mcp.tool(description="Get options chain — calls and puts for an expiration date")
def get_options_chain(symbol: str, date: Optional[str] = None):
    """Get options chain (calls and puts).

    Args:
        symbol: Ticker symbol.
        date: Expiration date (YYYY-MM-DD). If None, returns nearest expiration.

    Returns:
        Dict with "calls" and "puts" lists.
    """
    return _options.get_options_chain(symbol, date)


# -------- News tools --------
@mcp.tool(description="Get recent news articles for a symbol")
def get_news(symbol: str, count: int = 10):
    """Get recent news articles.

    Args:
        symbol: Ticker symbol.
        count: Number of articles (default 10).

    Returns:
        List of news article dicts.
    """
    return _news.get_news(symbol, count)


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        from mcp_http_compat import serve_http

        serve_http(mcp, host="127.0.0.1", port=9301, path="/mcp")
    else:
        mcp.run()
