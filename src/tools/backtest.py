"""Backtesting tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_db
from ..backtest.engine import run_backtest
from ..backtest.metrics import calculate_metrics


def register_backtest_tools(server: Server) -> None:
    @server.tool()
    async def futu_backtest(
        strategy_id: str,
        symbols: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
    ) -> str:
        """Run a backtest for a strategy against historical data.

        Args:
            strategy_id: Strategy ID to backtest.
            symbols: Comma-separated stock codes, e.g. "HK.00700,HK.09988".
            start_date: Start date, e.g. "2024-01-01".
            end_date: End date, e.g. "2024-12-31".
            initial_capital: Starting capital (default 100000).
        """
        db = get_db()
        row = db.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
        if not row:
            return f"❌ 策略 {strategy_id} 不存在"

        try:
            client = get_shared_client()
            symbol_list = [s.strip() for s in symbols.split(",")]
            rules = json.loads(row["rules"]) if row["rules"] else []
            risk_mgmt = json.loads(row["risk_management"]) if row["risk_management"] else {}

            # Fetch historical data for all symbols
            all_klines = {}
            for symbol in symbol_list:
                klines = client.request_history_kline(
                    symbol, start=start_date, end=end_date, ktype="K_DAY", max_count=1000
                )
                all_klines[symbol] = [
                    {"date": k.time_key, "open": k.open, "high": k.high,
                     "low": k.low, "close": k.close, "volume": k.volume}
                    for k in klines
                ]

            # Run backtest
            result = run_backtest(
                rules=rules,
                risk_management=risk_mgmt,
                klines=all_klines,
                initial_capital=initial_capital,
            )

            # Calculate metrics
            metrics = calculate_metrics(result["equity_curve"], result["trades"], initial_capital)

            # Save backtest result
            bt_id = str(uuid.uuid4())[:8]
            config_json = json.dumps({
                "symbols": symbol_list, "start_date": start_date,
                "end_date": end_date, "initial_capital": initial_capital,
            })
            result_json = json.dumps({"metrics": metrics, "trade_count": len(result["trades"])})
            db.execute(
                "INSERT INTO backtests (id, strategy_id, config, result) VALUES (?, ?, ?, ?)",
                (bt_id, strategy_id, config_json, result_json),
            )
            db.commit()

            # Format output
            total_return = metrics.get("total_return_pct", 0)
            ret_emoji = "🟢" if total_return >= 0 else "🔴"

            trade_list = result["trades"]
            wins = sum(1 for t in trade_list if t.get("pnl", 0) > 0)
            losses = sum(1 for t in trade_list if t.get("pnl", 0) < 0)

            return f"""## 📊 回测结果

**策略**: {row['name']} ({strategy_id})
**标的**: {symbols}
**周期**: {start_date} ~ {end_date}
**初始资金**: {initial_capital:,.2f}

### 核心指标

| 指标 | 数值 |
|------|------|
| 最终资产 | {metrics.get('final_equity', initial_capital):,.2f} |
| 总收益率 | {ret_emoji} {total_return:+.2f}% |
| 年化收益 | {metrics.get('annual_return_pct', 0):+.2f}% |
| Sharpe Ratio | {metrics.get('sharpe_ratio', 0):.2f} |
| 最大回撤 | {metrics.get('max_drawdown_pct', 0):.2f}% |
| 胜率 | {metrics.get('win_rate', 0):.1f}% |
| 盈亏比 | {metrics.get('profit_factor', 0):.2f} |
| 交易次数 | {len(trade_list)} (盈: {wins}, 亏: {losses}) |

### 对比基准
*建议与买入并持有策略对比（港股: HSI, 美股: SPY, A股: CSI300）*

**回测ID**: {bt_id}"""

        except Exception as e:
            return f"❌ 回测失败: {e}"

    @server.tool()
    async def futu_get_backtest_results(backtest_id: str) -> str:
        """Get results of a previous backtest.

        Args:
            backtest_id: Backtest ID.
        """
        db = get_db()
        row = db.execute("SELECT * FROM backtests WHERE id = ?", (backtest_id,)).fetchone()
        if not row:
            return f"❌ 回测 {backtest_id} 不存在"

        config = json.loads(row["config"])
        result = json.loads(row["result"])
        metrics = result.get("metrics", {})

        return f"""## 📊 回测结果 ({backtest_id})

**策略ID**: {row['strategy_id']}
**标的**: {', '.join(config.get('symbols', []))}
**周期**: {config.get('start_date')} ~ {config.get('end_date')}
**初始资金**: {config.get('initial_capital', 0):,.2f}
**创建时间**: {row['created_at']}

### 指标

| 指标 | 数值 |
|------|------|
| 最终资产 | {metrics.get('final_equity', 0):,.2f} |
| 总收益率 | {metrics.get('total_return_pct', 0):+.2f}% |
| Sharpe Ratio | {metrics.get('sharpe_ratio', 0):.2f} |
| 最大回撤 | {metrics.get('max_drawdown_pct', 0):.2f}% |
| 胜率 | {metrics.get('win_rate', 0):.1f}% |
| 交易次数 | {result.get('trade_count', 0)} |"""
