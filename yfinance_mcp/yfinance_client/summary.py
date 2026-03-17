from typing import Any, Dict

from .base import _df_to_dict, _ticker


class SummaryAPI:
    """Company fundamentals, financials, and analyst data."""

    def get_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile (sector, industry, description, officers, website).

        Args:
            symbol: Ticker symbol.

        Returns:
            Dict with company profile.
        """
        info = _ticker(symbol).get_info()
        profile_keys = [
            "sector", "industry", "longBusinessSummary", "website",
            "fullTimeEmployees", "companyOfficers", "city", "state",
            "country", "address1", "zip", "phone",
            "longName", "shortName", "symbol", "exchange",
        ]
        return {k: info[k] for k in profile_keys if k in info}

    def get_financials(
        self, symbol: str, freq: str = "yearly"
    ) -> Dict[str, Any]:
        """Get income statement.

        Args:
            symbol: Ticker symbol.
            freq: "yearly" or "quarterly".

        Returns:
            List of income statement records.
        """
        return _df_to_dict(_ticker(symbol).get_income_stmt(freq=freq))

    def get_balance_sheet(
        self, symbol: str, freq: str = "yearly"
    ) -> Dict[str, Any]:
        """Get balance sheet.

        Args:
            symbol: Ticker symbol.
            freq: "yearly" or "quarterly".

        Returns:
            List of balance sheet records.
        """
        return _df_to_dict(_ticker(symbol).get_balance_sheet(freq=freq))

    def get_earnings(self, symbol: str, freq: str = "yearly") -> Dict[str, Any]:
        """Get earnings data.

        Args:
            symbol: Ticker symbol.
            freq: "yearly" or "quarterly".

        Returns:
            List of earnings records.
        """
        return _df_to_dict(_ticker(symbol).get_earnings(freq=freq))

    def get_analyst_price_targets(self, symbol: str) -> Dict[str, Any]:
        """Get analyst price targets (low, current, mean, median, high).

        Args:
            symbol: Ticker symbol.

        Returns:
            Dict with analyst price target data.
        """
        return _ticker(symbol).get_analyst_price_targets()

    def get_recommendations(self, symbol: str) -> Dict[str, Any]:
        """Get analyst recommendation trends (buy, hold, sell, etc.).

        Args:
            symbol: Ticker symbol.

        Returns:
            List of recommendation records.
        """
        return _df_to_dict(_ticker(symbol).get_recommendations())
