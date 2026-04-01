"""Analytics & journaling tools — performance, trade journal, reviews."""

from __future__ import annotations

import json
from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_db, get_config


def register_analytics_tools(server: Server) -> None:
    @server.tool()
    async def futu_get_performance(period: str = "1m") -> str:
        """Get portfolio performance report.

        Args:
            period: Time period: 1d, 1w, 1m, 3m, 1y, all.
        """
        try:
            client = get_shared_client()
            positions = client.get_positions()
            account = client.get_account_info()

            total_pl = sum(p.pl_val for p in positions)
            total_mv = sum(p.market_val for p in positions)
            pl_emoji = "🟢" if total_pl >= 0 else "🔴"

            # Top gainers and losers
            sorted_by_pl = sorted(positions, key=lambda p: p.pl_ratio, reverse=True)
            top_gainers = sorted_by_pl[:3]
            top_losers = sorted_by_pl[-3:] if len(sorted_by_pl) > 3 else []

            lines = [f"## 📈 投资组合绩效 (期间: {period})\n"]
            lines.append(f"| 项目 | 数值 |")
            lines.append(f"|------|------|")
            lines.append(f"| 总资产 | {account.currency} {account.total_assets:,.2f} |")
            lines.append(f"| 持仓市值 | {account.currency} {total_mv:,.2f} |")
            lines.append(f"| 现金 | {account.currency} {account.cash:,.2f} |")
            lines.append(f"| 总盈亏 | {pl_emoji} {account.currency} {total_pl:,.2f} |")
            lines.append(f"| 持仓数 | {len(positions)} |")

            if top_gainers:
                lines.append("\n### 🏆 涨幅前三")
                for p in top_gainers:
                    if p.pl_ratio >= 0:
                        lines.append(f"- {p.name} ({p.code}): 🟢 {p.pl_ratio:+.2f}% ({p.pl_val:+,.2f})")

            if top_losers:
                lines.append("\n### 📉 跌幅前三")
                for p in reversed(top_losers):
                    if p.pl_ratio < 0:
                        lines.append(f"- {p.name} ({p.code}): 🔴 {p.pl_ratio:+.2f}% ({p.pl_val:+,.2f})")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取绩效失败: {e}"

    @server.tool()
    async def futu_get_trade_journal(
        start_date: str = "",
        end_date: str = "",
        symbol: str = "",
    ) -> str:
        """Get trade journal with all logged trades and notes.

        Args:
            start_date: Filter from date.
            end_date: Filter to date.
            symbol: Filter by stock code.
        """
        db = get_db()
        query = "SELECT * FROM trades WHERE 1=1"
        params: list = []

        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date + " 23:59:59")
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC LIMIT 100"
        rows = db.execute(query, params).fetchall()

        if not rows:
            return "📝 无交易记录"

        lines = ["## 📝 交易日志\n"]
        lines.append("| 时间 | 代码 | 方向 | 数量 | 价格 | 金额 | 状态 | 备注 |")
        lines.append("|------|------|------|------|------|------|------|------|")

        for r in rows:
            note = r["note"] or "—"
            lines.append(
                f"| {r['created_at']} | {r['symbol']} | {r['side']} | "
                f"{r['qty']:.0f} | {r['price'] or 0:.3f} | {r['total'] or 0:,.2f} | "
                f"{r['status']} | {note} |"
            )

        return "\n".join(lines)

    @server.tool()
    async def futu_add_trade_note(trade_id: str, note: str) -> str:
        """Add a note to a trade for journaling/review purposes.

        Args:
            trade_id: Trade ID from the journal.
            note: Note text to add.
        """
        db = get_db()
        row = db.execute("SELECT id FROM trades WHERE id = ?", (trade_id,)).fetchone()
        if not row:
            return f"❌ 交易 {trade_id} 不存在"

        db.execute("UPDATE trades SET note = ? WHERE id = ?", (note, trade_id))
        db.commit()
        return f"## ✅ 备注已添加\n\n**交易ID**: {trade_id}\n**备注**: {note}"

    @server.tool()
    async def futu_review_session(period: str = "1w", include_suggestions: bool = True) -> str:
        """Generate a trading review/recap for a given period.

        Args:
            period: Review period: 1d (today), 1w (this week), 1m (this month).
            include_suggestions: Include improvement suggestions.
        """
        db = get_db()

        # Map period to SQL filter
        period_map = {
            "1d": "datetime('now', '-1 day')",
            "1w": "datetime('now', '-7 days')",
            "1m": "datetime('now', '-30 days')",
        }
        since = period_map.get(period, period_map["1w"])

        trades = db.execute(
            f"SELECT * FROM trades WHERE created_at >= {since} ORDER BY created_at"
        ).fetchall()

        if not trades:
            return f"📝 在过去 {period} 内无交易记录"

        total_trades = len(trades)
        buys = sum(1 for t in trades if t["side"] == "BUY")
        sells = sum(1 for t in trades if t["side"] == "SELL")
        total_volume = sum(t["total"] or 0 for t in trades)
        symbols = set(t["symbol"] for t in trades)

        lines = [f"## 📝 交易复盘 (过去 {period})\n"]
        lines.append(f"| 项目 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总交易次数 | {total_trades} |")
        lines.append(f"| 买入次数 | {buys} |")
        lines.append(f"| 卖出次数 | {sells} |")
        lines.append(f"| 总交易金额 | {total_volume:,.2f} |")
        lines.append(f"| 涉及股票 | {len(symbols)} 只 |")
        lines.append(f"| 股票列表 | {', '.join(sorted(symbols))} |")

        # Recent trades summary
        lines.append("\n### 最近交易")
        lines.append("| 时间 | 代码 | 方向 | 数量 | 价格 | 状态 |")
        lines.append("|------|------|------|------|------|------|")
        for t in trades[-10:]:
            lines.append(
                f"| {t['created_at']} | {t['symbol']} | {t['side']} | "
                f"{t['qty']:.0f} | {t['price'] or 0:.3f} | {t['status']} |"
            )

        if include_suggestions:
            lines.append("\n### 💡 建议")
            if buys > 0 and sells == 0:
                lines.append("- 只有买入没有卖出，注意控制仓位")
            if total_trades > 20 and period == "1w":
                lines.append("- 交易频率较高，注意交易成本累积")
            if len(symbols) == 1:
                lines.append("- 交易集中在单一股票，注意分散风险")
            lines.append("- 建议为每笔交易添加备注，方便后续复盘")
            lines.append("- 定期检查止损设置是否合理")

        return "\n".join(lines)
