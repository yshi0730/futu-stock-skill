"""Account information tools."""

from __future__ import annotations

from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_config


def register_account_tools(server: Server) -> None:
    @server.tool()
    async def futu_get_account(market: str | None = None) -> str:
        """Get account information including balance, buying power, and positions value.

        Args:
            market: Market: HK, US, HKCC. Omit for default.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            info = client.get_account_info(market=mkt)
            env_label = "🟢 模拟盘" if info.trd_env == "SIMULATE" else "🔴 实盘"

            return f"""## 💰 账户信息 {env_label}

| 项目 | 数值 |
|------|------|
| 账户ID | {info.acc_id} |
| 总资产 | {info.currency} {info.total_assets:,.2f} |
| 现金 | {info.currency} {info.cash:,.2f} |
| 持仓市值 | {info.currency} {info.market_val:,.2f} |
| 购买力 | {info.currency} {info.power:,.2f} |
| 可用资金 | {info.currency} {info.available_funds:,.2f} |
| 冻结资金 | {info.currency} {info.frozen_cash:,.2f} |"""
        except Exception as e:
            return f"❌ 查询账户失败: {e}"

    @server.tool()
    async def futu_get_positions(market: str | None = None) -> str:
        """Get current positions with P&L information.

        Args:
            market: Market: HK, US, HKCC. Omit for default.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            positions = client.get_positions(market=mkt)

            if not positions:
                return "📋 当前无持仓"

            env = get_config("futu_trd_env") or "SIMULATE"
            env_label = "🟢 模拟盘" if env == "SIMULATE" else "🔴 实盘"

            lines = [f"## 📋 持仓列表 {env_label}\n"]
            lines.append("| 代码 | 名称 | 数量 | 可卖 | 成本价 | 现价 | 市值 | 盈亏 | 盈亏% |")
            lines.append("|------|------|------|------|--------|------|------|------|-------|")

            total_pl = 0.0
            total_mv = 0.0
            for p in positions:
                pl_emoji = "🟢" if p.pl_val >= 0 else "🔴"
                lines.append(
                    f"| {p.code} | {p.name} | {p.qty:.0f} | {p.can_sell_qty:.0f} | "
                    f"{p.cost_price:.3f} | {p.nominal_price:.3f} | {p.market_val:,.2f} | "
                    f"{pl_emoji} {p.pl_val:,.2f} | {p.pl_ratio:.2f}% |"
                )
                total_pl += p.pl_val
                total_mv += p.market_val

            pl_emoji = "🟢" if total_pl >= 0 else "🔴"
            lines.append(f"\n**总市值**: {total_mv:,.2f} | **总盈亏**: {pl_emoji} {total_pl:,.2f}")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 查询持仓失败: {e}"
