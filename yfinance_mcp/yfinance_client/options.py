from typing import Any, Dict, List, Optional

from .base import _df_to_dict, _ticker


class OptionsAPI:
    """Options chain data."""

    def get_options_expirations(self, symbol: str) -> List[str]:
        """Get available options expiration dates.

        Args:
            symbol: Ticker symbol.

        Returns:
            List of expiration date strings (YYYY-MM-DD).
        """
        return list(_ticker(symbol).options)

    def get_options_chain(
        self, symbol: str, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get options chain (calls and puts) for a given expiration date.

        Args:
            symbol: Ticker symbol.
            date: Expiration date string (YYYY-MM-DD).
                If None, returns the nearest expiration.

        Returns:
            Dict with "calls" and "puts" as lists of option contract records.
        """
        chain = _ticker(symbol).option_chain(date)
        return {
            "calls": _df_to_dict(chain.calls),
            "puts": _df_to_dict(chain.puts),
        }
