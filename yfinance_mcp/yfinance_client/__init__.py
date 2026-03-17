from .chart import ChartAPI
from .news import NewsAPI
from .options import OptionsAPI
from .quote import QuoteAPI
from .search import SearchAPI
from .summary import SummaryAPI


class YFinanceClient:
    """Main client for accessing Yahoo Finance data."""

    def __init__(self):
        self.chart = ChartAPI()
        self.news = NewsAPI()
        self.options = OptionsAPI()
        self.quote = QuoteAPI()
        self.search = SearchAPI()
        self.summary = SummaryAPI()


__all__ = [
    "YFinanceClient",
    "ChartAPI",
    "NewsAPI",
    "OptionsAPI",
    "QuoteAPI",
    "SearchAPI",
    "SummaryAPI",
]
