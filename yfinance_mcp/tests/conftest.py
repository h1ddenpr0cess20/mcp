import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd

from yfinance_client import (
    ChartAPI,
    NewsAPI,
    OptionsAPI,
    QuoteAPI,
    SearchAPI,
    SummaryAPI,
)


# --- API instance fixtures ---


@pytest.fixture
def quote_api():
    """QuoteAPI instance for testing."""
    return QuoteAPI()


@pytest.fixture
def chart_api():
    """ChartAPI instance for testing."""
    return ChartAPI()


@pytest.fixture
def search_api():
    """SearchAPI instance for testing."""
    return SearchAPI()


@pytest.fixture
def summary_api():
    """SummaryAPI instance for testing."""
    return SummaryAPI()


@pytest.fixture
def options_api():
    """OptionsAPI instance for testing."""
    return OptionsAPI()


@pytest.fixture
def news_api():
    """NewsAPI instance for testing."""
    return NewsAPI()


# --- Mock data fixtures ---


@pytest.fixture
def sample_info():
    """Sample ticker info dict as returned by yfinance."""
    return {
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Apple Inc. designs, manufactures...",
        "website": "https://www.apple.com",
        "fullTimeEmployees": 164000,
        "companyOfficers": [{"name": "Tim Cook", "title": "CEO"}],
        "city": "Cupertino",
        "state": "CA",
        "country": "United States",
        "address1": "One Apple Park Way",
        "zip": "95014",
        "phone": "408-996-1010",
        "longName": "Apple Inc.",
        "shortName": "Apple Inc.",
        "symbol": "AAPL",
        "exchange": "NMS",
        # Extra keys that get_profile should NOT include
        "previousClose": 175.0,
        "marketCap": 2800000000000,
        "fiftyTwoWeekHigh": 199.62,
    }


@pytest.fixture
def sample_history_df():
    """Sample DataFrame as returned by yfinance history()."""
    return pd.DataFrame(
        {
            "Open": [150.0, 151.0, 152.0],
            "High": [155.0, 156.0, 157.0],
            "Low": [149.0, 150.0, 151.0],
            "Close": [154.0, 155.0, 156.0],
            "Volume": [1000000, 1100000, 1200000],
        },
        index=pd.DatetimeIndex(
            ["2024-01-02", "2024-01-03", "2024-01-04"], name="Date"
        ),
    )


@pytest.fixture
def sample_options_chain():
    """Sample options chain namedtuple as returned by yfinance."""
    calls_df = pd.DataFrame(
        {
            "strike": [150.0, 155.0],
            "lastPrice": [5.50, 3.20],
            "bid": [5.40, 3.10],
            "ask": [5.60, 3.30],
            "volume": [100, 200],
        }
    )
    puts_df = pd.DataFrame(
        {
            "strike": [145.0, 140.0],
            "lastPrice": [2.10, 4.80],
            "bid": [2.00, 4.70],
            "ask": [2.20, 4.90],
            "volume": [50, 75],
        }
    )
    chain = Mock()
    chain.calls = calls_df
    chain.puts = puts_df
    return chain


@pytest.fixture
def mock_ticker(sample_info, sample_history_df):
    """A Mock yfinance.Ticker with common methods pre-configured."""
    ticker = MagicMock()
    ticker.get_info.return_value = sample_info
    ticker.get_fast_info.return_value = {
        "lastPrice": 175.0,
        "marketCap": 2800000000000,
        "volume": 55000000,
    }
    ticker.history.return_value = sample_history_df
    ticker.options = ("2024-03-15", "2024-04-19", "2024-05-17")
    ticker.get_income_stmt.return_value = pd.DataFrame(
        {"Revenue": [394328000000], "NetIncome": [96995000000]},
        index=pd.DatetimeIndex(["2023-09-30"]),
    )
    ticker.get_balance_sheet.return_value = pd.DataFrame(
        {"TotalAssets": [352583000000]},
        index=pd.DatetimeIndex(["2023-09-30"]),
    )
    ticker.get_earnings.return_value = pd.DataFrame(
        {"Revenue": [394328000000], "Earnings": [96995000000]},
        index=pd.DatetimeIndex(["2023-09-30"]),
    )
    ticker.get_analyst_price_targets.return_value = {
        "current": 175.0,
        "low": 140.0,
        "high": 220.0,
        "mean": 195.0,
        "median": 198.0,
    }
    ticker.get_recommendations.return_value = pd.DataFrame(
        {"period": ["0m"], "strongBuy": [12], "buy": [20], "hold": [8]},
    )
    ticker.get_news.return_value = [
        {"title": "Apple hits new high", "link": "https://example.com/1"},
        {"title": "Apple earnings beat", "link": "https://example.com/2"},
    ]
    return ticker
