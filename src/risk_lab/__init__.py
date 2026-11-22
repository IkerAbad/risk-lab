"""Risk Lab: one-day VaR and CVaR with a rolling backtest."""

from .backtest import rolling_backtest, summarize_backtest
from .data import (
    DEFAULT_TICKERS,
    DEFAULT_WEIGHTS,
    compute_returns,
    load_prices,
    portfolio_returns,
    weights_vector,
)
from .var import (
    RiskEstimate,
    historical_cvar,
    historical_risk,
    historical_var,
    monte_carlo_cvar,
    monte_carlo_risk,
    monte_carlo_var,
    parametric_cvar,
    parametric_risk,
    parametric_var,
    simulate_portfolio_returns,
)

__all__ = [
    "DEFAULT_TICKERS",
    "DEFAULT_WEIGHTS",
    "RiskEstimate",
    "compute_returns",
    "historical_cvar",
    "historical_risk",
    "historical_var",
    "load_prices",
    "monte_carlo_cvar",
    "monte_carlo_risk",
    "monte_carlo_var",
    "parametric_cvar",
    "parametric_risk",
    "parametric_var",
    "portfolio_returns",
    "rolling_backtest",
    "simulate_portfolio_returns",
    "summarize_backtest",
    "weights_vector",
]

__version__ = "0.1.0"
