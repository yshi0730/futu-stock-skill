"""Backtest performance metrics — Sharpe, drawdown, win rate, etc."""

from __future__ import annotations

import math


def calculate_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float,
) -> dict:
    """Calculate performance metrics from backtest results."""
    if not equity_curve:
        return {
            "final_equity": initial_capital,
            "total_return_pct": 0,
            "annual_return_pct": 0,
            "sharpe_ratio": 0,
            "max_drawdown_pct": 0,
            "win_rate": 0,
            "profit_factor": 0,
        }

    equities = [e["equity"] for e in equity_curve]
    final_equity = equities[-1]
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100

    # Annualized return
    n_days = len(equity_curve)
    years = n_days / 252 if n_days > 0 else 1
    annual_return_pct = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    # Daily returns
    daily_returns = []
    for i in range(1, len(equities)):
        if equities[i - 1] > 0:
            daily_returns.append((equities[i] - equities[i - 1]) / equities[i - 1])

    # Sharpe ratio (annualized, assuming risk-free rate = 0)
    sharpe_ratio = 0.0
    if daily_returns:
        mean_ret = sum(daily_returns) / len(daily_returns)
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1))
        if std_ret > 0:
            sharpe_ratio = (mean_ret / std_ret) * math.sqrt(252)

    # Max drawdown
    max_drawdown_pct = 0.0
    peak = equities[0]
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = ((peak - eq) / peak) * 100 if peak > 0 else 0
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

    # Win rate and profit factor
    closed_trades = [t for t in trades if t.get("side") == "SELL"]
    wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losses = [t for t in closed_trades if t.get("pnl", 0) < 0]

    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0

    gross_profit = sum(t["pnl"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

    return {
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annual_return_pct": round(annual_return_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.99,
        "total_trades": len(closed_trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }
