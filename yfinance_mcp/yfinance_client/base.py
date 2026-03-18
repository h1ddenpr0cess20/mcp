import pandas as pd
import yfinance as yf


def _ticker(symbol: str) -> yf.Ticker:
    """Create a yfinance Ticker instance."""
    return yf.Ticker(symbol)


def _df_to_dict(df) -> dict:
    """Convert a pandas DataFrame or Series to a JSON-serializable dict."""
    if df is None:
        return {}
    if isinstance(df, pd.Series):
        return df.to_dict()
    if isinstance(df, pd.DataFrame):
        # Convert Timestamp index/columns to strings
        df = df.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")
        for col in df.columns:
            if isinstance(df[col].dtype, pd.api.types.CategoricalDtype):
                df[col] = df[col].astype(str)
        return df.reset_index().to_dict(orient="records")
    return df
