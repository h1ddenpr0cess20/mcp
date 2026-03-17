"""Tests for the yfinance MCP client library.

Coverage strategy:
- base.py: _ticker creation, _df_to_dict with DataFrame/Series/None/passthrough
- quote.py: QuoteAPI -- get_info, get_fast_info, get_market_summary, get_market_status
- chart.py: ChartAPI -- get_history with period vs start/end branching
- search.py: SearchAPI -- search result structure
- summary.py: SummaryAPI -- profile key filtering, df-based methods, passthrough methods
- options.py: OptionsAPI -- expirations list, chain calls/puts structure
- news.py: NewsAPI -- get_news delegation and count arg
- Error paths: yfinance exceptions bubble up correctly
"""

import pandas as pd
import pytest
from unittest.mock import Mock, MagicMock, patch

from yfinance_client import (
    YFinanceClient,
    ChartAPI,
    NewsAPI,
    OptionsAPI,
    QuoteAPI,
    SearchAPI,
    SummaryAPI,
)
from yfinance_client.base import _ticker, _df_to_dict


# =============================================================================
# base.py -- _ticker and _df_to_dict
# =============================================================================


class TestTicker:
    """Tests for the _ticker helper."""

    @patch("yfinance_client.base.yf.Ticker")
    def test_creates_ticker_with_given_symbol(self, mock_ticker_cls):
        """Should pass the symbol string to yf.Ticker."""
        sentinel = object()
        mock_ticker_cls.return_value = sentinel

        result = _ticker("AAPL")

        mock_ticker_cls.assert_called_once_with("AAPL")
        assert result is sentinel

    @patch("yfinance_client.base.yf.Ticker")
    def test_passes_symbol_exactly_as_given(self, mock_ticker_cls):
        """Should not normalize or uppercase the symbol."""
        _ticker("btc-usd")
        mock_ticker_cls.assert_called_once_with("btc-usd")


class TestDfToDict:
    """Tests for the _df_to_dict helper."""

    def test_returns_empty_dict_for_none(self):
        """Should return {} when given None."""
        assert _df_to_dict(None) == {}

    def test_converts_series_to_dict(self):
        """Should call .to_dict() on a Series and return the result."""
        s = pd.Series({"a": 1, "b": 2, "c": 3})
        result = _df_to_dict(s)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_converts_dataframe_to_list_of_records(self):
        """Should return list of dicts with index included via reset_index."""
        df = pd.DataFrame(
            {"Open": [100.0, 101.0], "Close": [105.0, 106.0]},
            index=pd.Index(["AAPL", "GOOG"], name="Symbol"),
        )
        result = _df_to_dict(df)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"Symbol": "AAPL", "Open": 100.0, "Close": 105.0}
        assert result[1] == {"Symbol": "GOOG", "Open": 101.0, "Close": 106.0}

    def test_converts_datetime_index_to_strings(self):
        """Should format DatetimeIndex values as YYYY-MM-DD strings."""
        df = pd.DataFrame(
            {"Value": [10, 20]},
            index=pd.DatetimeIndex(["2024-01-15", "2024-06-30"], name="Date"),
        )
        result = _df_to_dict(df)
        assert result[0]["Date"] == "2024-01-15"
        assert result[1]["Date"] == "2024-06-30"

    def test_converts_categorical_columns_to_strings(self):
        """Should cast categorical dtype columns to strings."""
        df = pd.DataFrame({"grade": pd.Categorical(["A", "B", "A"])})
        result = _df_to_dict(df)
        assert all(isinstance(row["grade"], str) for row in result)
        assert result[0]["grade"] == "A"
        assert result[1]["grade"] == "B"

    def test_passthrough_for_non_pandas_types(self):
        """Should return the value unchanged if it's not None, Series, or DataFrame."""
        raw_dict = {"key": "value"}
        assert _df_to_dict(raw_dict) is raw_dict

        raw_list = [1, 2, 3]
        assert _df_to_dict(raw_list) is raw_list

        assert _df_to_dict("hello") == "hello"
        assert _df_to_dict(42) == 42

    def test_does_not_mutate_original_dataframe(self):
        """Should copy the DataFrame before modifying the index."""
        df = pd.DataFrame(
            {"Value": [1]},
            index=pd.DatetimeIndex(["2024-01-01"], name="Date"),
        )
        _df_to_dict(df)
        # Original should still have DatetimeIndex
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_empty_dataframe_returns_empty_list(self):
        """Should return an empty list for an empty DataFrame."""
        df = pd.DataFrame(columns=["A", "B"])
        result = _df_to_dict(df)
        assert result == []

    def test_empty_series_returns_empty_dict(self):
        """Should return an empty dict for an empty Series."""
        s = pd.Series(dtype=float)
        result = _df_to_dict(s)
        assert result == {}


# =============================================================================
# quote.py -- QuoteAPI
# =============================================================================


class TestQuoteAPI:
    """Tests for QuoteAPI methods."""

    @patch("yfinance_client.quote._ticker")
    def test_get_info_returns_ticker_info(self, mock_ticker_fn, quote_api):
        """Should delegate to ticker.get_info() and return the result."""
        expected = {"symbol": "AAPL", "shortName": "Apple Inc."}
        mock_ticker_fn.return_value.get_info.return_value = expected

        result = quote_api.get_info("AAPL")

        mock_ticker_fn.assert_called_once_with("AAPL")
        mock_ticker_fn.return_value.get_info.assert_called_once()
        assert result == expected

    @patch("yfinance_client.quote._ticker")
    def test_get_fast_info_wraps_result_in_dict(self, mock_ticker_fn, quote_api):
        """Should call dict() on the fast_info object to serialize it."""
        fast_info_obj = MagicMock()
        # dict(fast_info_obj) iterates it -- simulate a dict-like object
        fast_info_data = {"lastPrice": 175.0, "marketCap": 2800000000000}
        fast_info_obj.__iter__ = Mock(return_value=iter(fast_info_data))
        fast_info_obj.__getitem__ = fast_info_data.__getitem__
        # The code does dict(fi), so we mock get_fast_info to return a real dict
        mock_ticker_fn.return_value.get_fast_info.return_value = fast_info_data

        result = quote_api.get_fast_info("MSFT")

        mock_ticker_fn.assert_called_once_with("MSFT")
        assert result == fast_info_data

    @patch("yfinance_client.quote.yf.Market")
    def test_get_market_summary_uses_market_arg(self, mock_market_cls, quote_api):
        """Should create yf.Market with the given market and return .summary."""
        mock_market = Mock()
        mock_market.summary = {"^GSPC": {"price": 5000}}
        mock_market_cls.return_value = mock_market

        result = quote_api.get_market_summary("gb_market")

        mock_market_cls.assert_called_once_with("gb_market")
        assert result == {"^GSPC": {"price": 5000}}

    @patch("yfinance_client.quote.yf.Market")
    def test_get_market_summary_default_us_market(self, mock_market_cls, quote_api):
        """Should default to 'us_market' when no market argument provided."""
        mock_market = Mock()
        mock_market.summary = {}
        mock_market_cls.return_value = mock_market

        quote_api.get_market_summary()

        mock_market_cls.assert_called_once_with("us_market")

    @patch("yfinance_client.quote.yf.Market")
    def test_get_market_status_converts_values_to_strings(
        self, mock_market_cls, quote_api
    ):
        """Should stringify all values in the status dict for JSON compat."""
        from datetime import datetime

        mock_market = Mock()
        mock_market.status = {
            "market_state": "REGULAR",
            "open_time": datetime(2024, 1, 15, 9, 30),
            "close_time": datetime(2024, 1, 15, 16, 0),
        }
        mock_market_cls.return_value = mock_market

        result = quote_api.get_market_status("us_market")

        assert result["market_state"] == "REGULAR"
        assert result["open_time"] == str(datetime(2024, 1, 15, 9, 30))
        assert result["close_time"] == str(datetime(2024, 1, 15, 16, 0))

    @patch("yfinance_client.quote.yf.Market")
    def test_get_market_status_handles_non_stringifiable_values(
        self, mock_market_cls, quote_api
    ):
        """Should fall back to raw value if str() raises."""

        class Unstringable:
            def __str__(self):
                raise TypeError("cannot stringify")

        obj = Unstringable()
        mock_market = Mock()
        mock_market.status = {"weird_field": obj}
        mock_market_cls.return_value = mock_market

        result = quote_api.get_market_status()

        assert result["weird_field"] is obj

    @patch("yfinance_client.quote._ticker")
    def test_get_info_propagates_exception(self, mock_ticker_fn, quote_api):
        """Should not swallow exceptions from yfinance."""
        mock_ticker_fn.return_value.get_info.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            quote_api.get_info("INVALID")


# =============================================================================
# chart.py -- ChartAPI
# =============================================================================


class TestChartAPI:
    """Tests for ChartAPI.get_history keyword argument logic."""

    @patch("yfinance_client.chart._ticker")
    def test_get_history_default_uses_period(self, mock_ticker_fn, chart_api):
        """Should pass period (not start) when start is not provided."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        chart_api.get_history("AAPL")

        call_kwargs = mock_ticker_fn.return_value.history.call_args[1]
        assert call_kwargs["period"] == "1mo"
        assert "start" not in call_kwargs
        assert call_kwargs["interval"] == "1d"
        assert call_kwargs["prepost"] is False
        assert call_kwargs["actions"] is True

    @patch("yfinance_client.chart._ticker")
    def test_get_history_with_start_omits_period(self, mock_ticker_fn, chart_api):
        """Should use start/end instead of period when start is provided."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        chart_api.get_history("AAPL", start="2024-01-01", end="2024-06-30")

        call_kwargs = mock_ticker_fn.return_value.history.call_args[1]
        assert call_kwargs["start"] == "2024-01-01"
        assert call_kwargs["end"] == "2024-06-30"
        assert "period" not in call_kwargs

    @patch("yfinance_client.chart._ticker")
    def test_get_history_with_start_only_no_end(self, mock_ticker_fn, chart_api):
        """Should include start but not end when only start is given."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        chart_api.get_history("GOOG", start="2024-01-01")

        call_kwargs = mock_ticker_fn.return_value.history.call_args[1]
        assert call_kwargs["start"] == "2024-01-01"
        assert "end" not in call_kwargs
        assert "period" not in call_kwargs

    @patch("yfinance_client.chart._ticker")
    def test_get_history_custom_interval_and_prepost(self, mock_ticker_fn, chart_api):
        """Should forward interval and prepost args to yfinance."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        chart_api.get_history("TSLA", period="5d", interval="1h", prepost=True)

        call_kwargs = mock_ticker_fn.return_value.history.call_args[1]
        assert call_kwargs["period"] == "5d"
        assert call_kwargs["interval"] == "1h"
        assert call_kwargs["prepost"] is True

    @patch("yfinance_client.chart._ticker")
    def test_get_history_returns_converted_dataframe(
        self, mock_ticker_fn, chart_api, sample_history_df
    ):
        """Should convert the returned DataFrame to list of record dicts."""
        mock_ticker_fn.return_value.history.return_value = sample_history_df

        result = chart_api.get_history("AAPL")

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["Date"] == "2024-01-02"
        assert result[0]["Open"] == 150.0
        assert result[0]["Close"] == 154.0
        assert result[2]["Volume"] == 1200000

    @patch("yfinance_client.chart._ticker")
    def test_get_history_empty_dataframe_returns_empty_list(
        self, mock_ticker_fn, chart_api
    ):
        """Should return [] when yfinance returns an empty DataFrame."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        result = chart_api.get_history("AAPL")

        assert result == []

    @patch("yfinance_client.chart._ticker")
    def test_get_history_actions_false(self, mock_ticker_fn, chart_api):
        """Should pass actions=False through to yfinance."""
        mock_ticker_fn.return_value.history.return_value = pd.DataFrame()

        chart_api.get_history("AAPL", actions=False)

        call_kwargs = mock_ticker_fn.return_value.history.call_args[1]
        assert call_kwargs["actions"] is False


# =============================================================================
# search.py -- SearchAPI
# =============================================================================


class TestSearchAPI:
    """Tests for SearchAPI.search."""

    @patch("yfinance_client.search.yf.Search")
    def test_search_returns_quotes_and_news(self, mock_search_cls, search_api):
        """Should return dict with 'quotes' and 'news' keys from Search object."""
        mock_search = Mock()
        mock_search.quotes = [
            {"symbol": "AAPL", "shortname": "Apple Inc."},
            {"symbol": "AAPD", "shortname": "Direxion Daily AAPL Bear"},
        ]
        mock_search.news = [{"title": "Apple news article"}]
        mock_search_cls.return_value = mock_search

        result = search_api.search("Apple")

        mock_search_cls.assert_called_once_with(
            "Apple", max_results=8, news_count=8
        )
        assert result["quotes"] == mock_search.quotes
        assert result["news"] == mock_search.news

    @patch("yfinance_client.search.yf.Search")
    def test_search_custom_limits(self, mock_search_cls, search_api):
        """Should forward max_results and news_count to yf.Search."""
        mock_search = Mock()
        mock_search.quotes = []
        mock_search.news = []
        mock_search_cls.return_value = mock_search

        search_api.search("Tesla", max_results=3, news_count=5)

        mock_search_cls.assert_called_once_with(
            "Tesla", max_results=3, news_count=5
        )

    @patch("yfinance_client.search.yf.Search")
    def test_search_empty_results(self, mock_search_cls, search_api):
        """Should return empty lists when no results found."""
        mock_search = Mock()
        mock_search.quotes = []
        mock_search.news = []
        mock_search_cls.return_value = mock_search

        result = search_api.search("xyznonexistent")

        assert result == {"quotes": [], "news": []}


# =============================================================================
# summary.py -- SummaryAPI
# =============================================================================


class TestSummaryAPI:
    """Tests for SummaryAPI methods."""

    @patch("yfinance_client.summary._ticker")
    def test_get_profile_filters_to_expected_keys(
        self, mock_ticker_fn, summary_api, sample_info
    ):
        """Should only include the defined profile_keys from info dict."""
        mock_ticker_fn.return_value.get_info.return_value = sample_info

        result = summary_api.get_profile("AAPL")

        expected_keys = {
            "sector", "industry", "longBusinessSummary", "website",
            "fullTimeEmployees", "companyOfficers", "city", "state",
            "country", "address1", "zip", "phone",
            "longName", "shortName", "symbol", "exchange",
        }
        assert set(result.keys()) == expected_keys
        # Verify excluded keys are NOT present
        assert "previousClose" not in result
        assert "marketCap" not in result
        assert "fiftyTwoWeekHigh" not in result

    @patch("yfinance_client.summary._ticker")
    def test_get_profile_values_match_source(
        self, mock_ticker_fn, summary_api, sample_info
    ):
        """Should preserve the actual values from info for included keys."""
        mock_ticker_fn.return_value.get_info.return_value = sample_info

        result = summary_api.get_profile("AAPL")

        assert result["sector"] == "Technology"
        assert result["longName"] == "Apple Inc."
        assert result["fullTimeEmployees"] == 164000

    @patch("yfinance_client.summary._ticker")
    def test_get_profile_skips_missing_keys(self, mock_ticker_fn, summary_api):
        """Should silently omit keys that are absent from the info dict."""
        sparse_info = {"symbol": "PRIVATE", "shortName": "Private Co."}
        mock_ticker_fn.return_value.get_info.return_value = sparse_info

        result = summary_api.get_profile("PRIVATE")

        assert result == {"symbol": "PRIVATE", "shortName": "Private Co."}
        assert "sector" not in result

    @patch("yfinance_client.summary._ticker")
    def test_get_financials_yearly(self, mock_ticker_fn, summary_api):
        """Should call get_income_stmt with freq='yearly'."""
        mock_df = pd.DataFrame({"Revenue": [100]})
        mock_ticker_fn.return_value.get_income_stmt.return_value = mock_df

        result = summary_api.get_financials("AAPL")

        mock_ticker_fn.return_value.get_income_stmt.assert_called_once_with(
            freq="yearly"
        )
        assert isinstance(result, list)

    @patch("yfinance_client.summary._ticker")
    def test_get_financials_quarterly(self, mock_ticker_fn, summary_api):
        """Should pass freq='quarterly' to get_income_stmt."""
        mock_df = pd.DataFrame({"Revenue": [50]})
        mock_ticker_fn.return_value.get_income_stmt.return_value = mock_df

        summary_api.get_financials("AAPL", freq="quarterly")

        mock_ticker_fn.return_value.get_income_stmt.assert_called_once_with(
            freq="quarterly"
        )

    @patch("yfinance_client.summary._ticker")
    def test_get_balance_sheet_delegates_correctly(self, mock_ticker_fn, summary_api):
        """Should call get_balance_sheet on ticker with correct freq."""
        mock_df = pd.DataFrame({"TotalAssets": [300000]})
        mock_ticker_fn.return_value.get_balance_sheet.return_value = mock_df

        result = summary_api.get_balance_sheet("MSFT", freq="quarterly")

        mock_ticker_fn.assert_called_once_with("MSFT")
        mock_ticker_fn.return_value.get_balance_sheet.assert_called_once_with(
            freq="quarterly"
        )
        assert isinstance(result, list)

    @patch("yfinance_client.summary._ticker")
    def test_get_earnings_delegates_correctly(self, mock_ticker_fn, summary_api):
        """Should call get_earnings on ticker with correct freq."""
        mock_df = pd.DataFrame({"Earnings": [50000]})
        mock_ticker_fn.return_value.get_earnings.return_value = mock_df

        result = summary_api.get_earnings("GOOG")

        mock_ticker_fn.return_value.get_earnings.assert_called_once_with(
            freq="yearly"
        )
        assert isinstance(result, list)

    @patch("yfinance_client.summary._ticker")
    def test_get_analyst_price_targets_returns_dict(self, mock_ticker_fn, summary_api):
        """Should return the raw dict from ticker.get_analyst_price_targets()."""
        expected = {"current": 175.0, "low": 140.0, "high": 220.0}
        mock_ticker_fn.return_value.get_analyst_price_targets.return_value = expected

        result = summary_api.get_analyst_price_targets("AAPL")

        mock_ticker_fn.assert_called_once_with("AAPL")
        assert result == expected

    @patch("yfinance_client.summary._ticker")
    def test_get_recommendations_converts_dataframe(self, mock_ticker_fn, summary_api):
        """Should convert recommendations DataFrame to list of records."""
        rec_df = pd.DataFrame(
            {"period": ["0m", "-1m"], "strongBuy": [12, 10], "buy": [20, 18]}
        )
        mock_ticker_fn.return_value.get_recommendations.return_value = rec_df

        result = summary_api.get_recommendations("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["strongBuy"] == 12
        assert result[1]["buy"] == 18

    @patch("yfinance_client.summary._ticker")
    def test_get_recommendations_handles_none(self, mock_ticker_fn, summary_api):
        """Should return {} when yfinance returns None for recommendations."""
        mock_ticker_fn.return_value.get_recommendations.return_value = None

        result = summary_api.get_recommendations("AAPL")

        assert result == {}


# =============================================================================
# options.py -- OptionsAPI
# =============================================================================


class TestOptionsAPI:
    """Tests for OptionsAPI methods."""

    @patch("yfinance_client.options._ticker")
    def test_get_options_expirations_returns_list(self, mock_ticker_fn, options_api):
        """Should convert the tuple of expiration dates to a list."""
        mock_ticker_fn.return_value.options = (
            "2024-03-15",
            "2024-04-19",
            "2024-05-17",
        )

        result = options_api.get_options_expirations("AAPL")

        mock_ticker_fn.assert_called_once_with("AAPL")
        assert result == ["2024-03-15", "2024-04-19", "2024-05-17"]
        assert isinstance(result, list)

    @patch("yfinance_client.options._ticker")
    def test_get_options_expirations_empty(self, mock_ticker_fn, options_api):
        """Should return empty list when no options available."""
        mock_ticker_fn.return_value.options = ()

        result = options_api.get_options_expirations("NOOPT")

        assert result == []

    @patch("yfinance_client.options._ticker")
    def test_get_options_chain_returns_calls_and_puts(
        self, mock_ticker_fn, options_api, sample_options_chain
    ):
        """Should return dict with 'calls' and 'puts' as record lists."""
        mock_ticker_fn.return_value.option_chain.return_value = sample_options_chain

        result = options_api.get_options_chain("AAPL", date="2024-03-15")

        mock_ticker_fn.return_value.option_chain.assert_called_once_with("2024-03-15")
        assert "calls" in result
        assert "puts" in result
        assert isinstance(result["calls"], list)
        assert isinstance(result["puts"], list)
        assert len(result["calls"]) == 2
        assert len(result["puts"]) == 2
        assert result["calls"][0]["strike"] == 150.0
        assert result["puts"][1]["lastPrice"] == 4.80

    @patch("yfinance_client.options._ticker")
    def test_get_options_chain_default_date_is_none(
        self, mock_ticker_fn, options_api, sample_options_chain
    ):
        """Should pass None to option_chain when no date given."""
        mock_ticker_fn.return_value.option_chain.return_value = sample_options_chain

        options_api.get_options_chain("AAPL")

        mock_ticker_fn.return_value.option_chain.assert_called_once_with(None)


# =============================================================================
# news.py -- NewsAPI
# =============================================================================


class TestNewsAPI:
    """Tests for NewsAPI methods."""

    @patch("yfinance_client.news._ticker")
    def test_get_news_returns_list_of_articles(self, mock_ticker_fn, news_api):
        """Should delegate to ticker.get_news and return the list directly."""
        articles = [
            {"title": "Article 1", "link": "https://example.com/1"},
            {"title": "Article 2", "link": "https://example.com/2"},
        ]
        mock_ticker_fn.return_value.get_news.return_value = articles

        result = news_api.get_news("AAPL")

        mock_ticker_fn.assert_called_once_with("AAPL")
        mock_ticker_fn.return_value.get_news.assert_called_once_with(count=10)
        assert result == articles

    @patch("yfinance_client.news._ticker")
    def test_get_news_custom_count(self, mock_ticker_fn, news_api):
        """Should forward the count parameter to yfinance."""
        mock_ticker_fn.return_value.get_news.return_value = []

        news_api.get_news("TSLA", count=5)

        mock_ticker_fn.return_value.get_news.assert_called_once_with(count=5)

    @patch("yfinance_client.news._ticker")
    def test_get_news_empty_result(self, mock_ticker_fn, news_api):
        """Should return an empty list when no news available."""
        mock_ticker_fn.return_value.get_news.return_value = []

        result = news_api.get_news("UNKNOWN")

        assert result == []

    @patch("yfinance_client.news._ticker")
    def test_get_news_propagates_exception(self, mock_ticker_fn, news_api):
        """Should not swallow exceptions from yfinance."""
        mock_ticker_fn.return_value.get_news.side_effect = RuntimeError("API limit")

        with pytest.raises(RuntimeError, match="API limit"):
            news_api.get_news("AAPL")


# =============================================================================
# __init__.py -- YFinanceClient composition
# =============================================================================


class TestYFinanceClient:
    """Tests for the top-level YFinanceClient composition."""

    def test_client_exposes_all_api_instances(self):
        """Should create sub-API instances as attributes."""
        client = YFinanceClient()

        assert isinstance(client.chart, ChartAPI)
        assert isinstance(client.news, NewsAPI)
        assert isinstance(client.options, OptionsAPI)
        assert isinstance(client.quote, QuoteAPI)
        assert isinstance(client.search, SearchAPI)
        assert isinstance(client.summary, SummaryAPI)

    def test_client_api_instances_are_distinct(self):
        """Each sub-API should be its own instance, not shared."""
        client = YFinanceClient()

        apis = [
            client.chart,
            client.news,
            client.options,
            client.quote,
            client.search,
            client.summary,
        ]
        # All should be different objects
        ids = [id(api) for api in apis]
        assert len(set(ids)) == len(ids)
