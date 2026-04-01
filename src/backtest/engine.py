"""Simple backtest engine — executes strategy rules against historical K-line data."""

from __future__ import annotations

from typing import Any


def _compute_sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _evaluate_condition(
    condition: dict,
    closes: list[float],
    prev_closes: list[float],
) -> bool:
    """Evaluate a single strategy condition against price data."""
    indicator = condition.get("indicator", "")
    op = condition.get("op", "")
    params = condition.get("params", {})
    value = condition.get("value")

    if indicator == "sma":
        period = params.get("period", 20)
        sma_val = _compute_sma(closes, period)
        if sma_val is None:
            return False
        target = condition.get("target", "price")
        if target == "price":
            target_val = closes[-1]
        elif target == "sma":
            target_period = condition.get("target_params", {}).get("period", 50)
            target_val = _compute_sma(closes, target_period)
            if target_val is None:
                return False
        else:
            return False

        if op == "cross_above":
            prev_sma = _compute_sma(prev_closes, period)
            if prev_sma is None:
                return False
            if target == "sma":
                prev_target = _compute_sma(prev_closes, condition.get("target_params", {}).get("period", 50))
                if prev_target is None:
                    return False
                return prev_sma <= prev_target and sma_val > target_val
            return prev_sma <= prev_closes[-1] and sma_val > closes[-1]
        elif op == "cross_below":
            prev_sma = _compute_sma(prev_closes, period)
            if prev_sma is None:
                return False
            if target == "sma":
                prev_target = _compute_sma(prev_closes, condition.get("target_params", {}).get("period", 50))
                if prev_target is None:
                    return False
                return prev_sma >= prev_target and sma_val < target_val
            return prev_sma >= prev_closes[-1] and sma_val < closes[-1]

    elif indicator == "price_vs_sma":
        period = params.get("period", 20)
        sma_val = _compute_sma(closes, period)
        if sma_val is None or sma_val == 0:
            return False
        deviation = ((closes[-1] - sma_val) / sma_val) * 100
        if op == "lt":
            return deviation < (value or 0)
        elif op == "gt":
            return deviation > (value or 0)

    elif indicator == "change_rate":
        period = params.get("period", 20)
        if len(closes) < period + 1:
            return False
        change = ((closes[-1] - closes[-period - 1]) / closes[-period - 1]) * 100
        if op == "gt":
            return change > (value or 0)
        elif op == "lt":
            return change < (value or 0)

    elif indicator == "price_change_pct":
        if len(closes) < 2:
            return False
        change = ((closes[-1] - closes[-2]) / closes[-2]) * 100
        if op == "lt":
            return change < (value or 0)
        elif op == "gt":
            return change > (value or 0)

    return False


def run_backtest(
    rules: list[dict],
    risk_management: dict,
    klines: dict[str, list[dict]],
    initial_capital: float = 100000.0,
) -> dict[str, Any]:
    """Run a backtest.

    Args:
        rules: Strategy rules.
        risk_management: Risk management parameters.
        klines: Dict of symbol -> list of {date, open, high, low, close, volume}.
        initial_capital: Starting capital.

    Returns:
        Dict with equity_curve and trades.
    """
    cash = initial_capital
    positions: dict[str, dict] = {}  # symbol -> {qty, avg_price}
    trades: list[dict] = []
    equity_curve: list[dict] = []

    stop_loss_pct = risk_management.get("stop_loss_pct", 100)
    take_profit_pct = risk_management.get("take_profit_pct", 100)
    max_position_pct = risk_management.get("max_position_pct", 100)

    # Get all unique dates
    all_dates: list[str] = []
    for symbol, bars in klines.items():
        for bar in bars:
            if bar["date"] not in all_dates:
                all_dates.append(bar["date"])
    all_dates.sort()

    # Index klines by date
    kline_idx: dict[str, dict[str, dict]] = {}
    for symbol, bars in klines.items():
        kline_idx[symbol] = {bar["date"]: bar for bar in bars}

    for i, date in enumerate(all_dates):
        # Check stop loss and take profit for existing positions
        for symbol in list(positions.keys()):
            if symbol not in kline_idx or date not in kline_idx[symbol]:
                continue
            bar = kline_idx[symbol][date]
            pos = positions[symbol]
            change_pct = ((bar["close"] - pos["avg_price"]) / pos["avg_price"]) * 100

            # Stop loss
            if change_pct <= -stop_loss_pct:
                pnl = (bar["close"] - pos["avg_price"]) * pos["qty"]
                cash += bar["close"] * pos["qty"]
                trades.append({
                    "date": date, "symbol": symbol, "side": "SELL",
                    "qty": pos["qty"], "price": bar["close"],
                    "pnl": pnl, "reason": "stop_loss",
                })
                del positions[symbol]
                continue

            # Take profit
            if change_pct >= take_profit_pct:
                pnl = (bar["close"] - pos["avg_price"]) * pos["qty"]
                cash += bar["close"] * pos["qty"]
                trades.append({
                    "date": date, "symbol": symbol, "side": "SELL",
                    "qty": pos["qty"], "price": bar["close"],
                    "pnl": pnl, "reason": "take_profit",
                })
                del positions[symbol]
                continue

        # Evaluate rules
        for rule in rules:
            conditions = rule.get("conditions", [])
            actions = rule.get("actions", [])

            for symbol in klines:
                if symbol not in kline_idx or date not in kline_idx[symbol]:
                    continue

                # Build close history up to this date
                closes = [
                    kline_idx[symbol][d]["close"]
                    for d in all_dates[:i + 1]
                    if d in kline_idx[symbol]
                ]
                prev_closes = closes[:-1] if len(closes) > 1 else closes

                # Check all conditions
                all_met = all(
                    _evaluate_condition(c, closes, prev_closes)
                    for c in conditions
                ) if conditions else False  # No conditions = don't trigger (safety)

                if not all_met:
                    continue

                bar = kline_idx[symbol][date]

                for action in actions:
                    action_type = action.get("type", "")

                    if action_type == "buy" and symbol not in positions:
                        # Calculate position size
                        sizing = action.get("sizing", "percent_of_equity")
                        total_equity = cash + sum(
                            kline_idx.get(s, {}).get(date, {}).get("close", 0) * p["qty"]
                            for s, p in positions.items()
                        )

                        if sizing == "percent_of_equity":
                            amount = total_equity * action.get("value", 10) / 100
                        elif sizing == "fixed_amount":
                            amount = action.get("value", 5000)
                        else:
                            amount = total_equity * 0.1

                        # Check max position size
                        if amount > total_equity * max_position_pct / 100:
                            amount = total_equity * max_position_pct / 100

                        if amount > cash:
                            amount = cash

                        qty = int(amount / bar["close"])
                        if qty <= 0:
                            continue

                        cost = qty * bar["close"]
                        cash -= cost
                        positions[symbol] = {"qty": qty, "avg_price": bar["close"]}
                        trades.append({
                            "date": date, "symbol": symbol, "side": "BUY",
                            "qty": qty, "price": bar["close"], "pnl": 0, "reason": "signal",
                        })

                    elif action_type == "sell" and symbol in positions:
                        sizing = action.get("sizing", "all")
                        pos = positions[symbol]

                        if sizing == "all":
                            sell_qty = pos["qty"]
                        else:
                            sell_qty = pos["qty"]

                        pnl = (bar["close"] - pos["avg_price"]) * sell_qty
                        cash += bar["close"] * sell_qty
                        trades.append({
                            "date": date, "symbol": symbol, "side": "SELL",
                            "qty": sell_qty, "price": bar["close"],
                            "pnl": pnl, "reason": "signal",
                        })
                        del positions[symbol]

        # Record equity
        portfolio_val = sum(
            kline_idx.get(s, {}).get(date, {}).get("close", p["avg_price"]) * p["qty"]
            for s, p in positions.items()
        )
        equity_curve.append({"date": date, "equity": cash + portfolio_val})

    return {"equity_curve": equity_curve, "trades": trades}
