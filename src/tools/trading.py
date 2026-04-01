"""Trading tools — order placement, modification, cancellation."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_db, get_config


def register_trading_tools(server: Server) -> None:
    @server.tool()
    async def futu_place_order(
        code: str,
        price: float,
        qty: int,
        trd_side: str = "BUY",
        order_type: str = "NORMAL",
        market: str | None = None,
        remark: str = "",
    ) -> str:
        """Place a stock order. Trade must be unlocked first.

        Args:
            code: Stock code, e.g. "HK.00700".
            price: Order price.
            qty: Order quantity (shares).
            trd_side: BUY, SELL, SELL_SHORT, BUY_BACK.
            order_type: NORMAL (limit), MARKET, ABSOLUTE_LIMIT, AUCTION, AUCTION_LIMIT, SPECIAL_LIMIT.
            market: Market override: HK, US, HKCC. Omit for auto-detect from code.
            remark: Optional order remark.
        """
        try:
            client = get_shared_client()
            env = get_config("futu_trd_env") or "SIMULATE"
            env_label = "🟢 模拟盘" if env == "SIMULATE" else "🔴 实盘"

            if not client.is_trade_unlocked:
                return "❌ 交易未解锁。请先调用 **futu_unlock_trade** 解锁交易。"

            from ..futu_client.types import MarketType, TradingEnv
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            trd_env = TradingEnv(env)

            order = client.place_order(
                code=code,
                price=price,
                qty=qty,
                trd_side=trd_side,
                order_type=order_type,
                market=mkt,
                trd_env=trd_env,
                remark=remark,
            )

            # Log trade to database
            db = get_db()
            trade_id = str(uuid.uuid4())[:8]
            db.execute(
                "INSERT INTO trades (id, order_id, symbol, side, qty, price, total, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (trade_id, order.order_id, code, trd_side, qty, price, price * qty, order.status),
            )
            db.commit()

            return f"""## ✅ 订单已提交 {env_label}

| 项目 | 详情 |
|------|------|
| 订单ID | {order.order_id} |
| 股票 | {order.name} ({code}) |
| 方向 | {trd_side} |
| 类型 | {order_type} |
| 价格 | {price:.3f} |
| 数量 | {qty} |
| 预估金额 | {price * qty:,.2f} |
| 状态 | {order.status} |"""
        except Exception as e:
            return f"❌ 下单失败: {e}"

    @server.tool()
    async def futu_modify_order(
        order_id: str,
        price: float,
        qty: int,
        market: str | None = None,
    ) -> str:
        """Modify an existing order's price and/or quantity.

        Args:
            order_id: Order ID to modify.
            price: New price.
            qty: New quantity.
            market: Market: HK, US, HKCC.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            result = client.modify_order(order_id, price, qty, market=mkt)

            return f"""## ✏️ 订单已修改

**订单ID**: {order_id}
**新价格**: {price:.3f}
**新数量**: {qty}"""
        except Exception as e:
            return f"❌ 修改订单失败: {e}"

    @server.tool()
    async def futu_cancel_order(order_id: str, market: str | None = None) -> str:
        """Cancel an existing order.

        Args:
            order_id: Order ID to cancel.
            market: Market: HK, US, HKCC.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            client.cancel_order(order_id, market=mkt)
            return f"## ❌ 订单已撤销\n\n**订单ID**: {order_id}"
        except Exception as e:
            return f"❌ 撤单失败: {e}"

    @server.tool()
    async def futu_cancel_all_orders(market: str | None = None) -> str:
        """Cancel ALL open orders. Use with caution!

        Args:
            market: Market: HK, US, HKCC.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            client.cancel_all_orders(market=mkt)
            return "## ⚠️ 已撤销全部订单"
        except Exception as e:
            return f"❌ 全部撤单失败: {e}"

    @server.tool()
    async def futu_get_orders(
        market: str | None = None,
        status: str | None = None,
    ) -> str:
        """Get current order list.

        Args:
            market: Market: HK, US, HKCC.
            status: Filter by status: SUBMITTED, FILLED_ALL, FILLED_PART, CANCELLED_ALL, FAILED. Comma-separated.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            status_filter = [s.strip() for s in status.split(",")] if status else None
            orders = client.get_order_list(market=mkt, status_filter=status_filter)

            if not orders:
                return "📋 当前无订单"

            env = get_config("futu_trd_env") or "SIMULATE"
            env_label = "🟢 模拟盘" if env == "SIMULATE" else "🔴 实盘"

            lines = [f"## 📋 订单列表 {env_label}\n"]
            lines.append("| 订单ID | 代码 | 名称 | 方向 | 价格 | 数量 | 已成交 | 成交价 | 状态 | 时间 |")
            lines.append("|--------|------|------|------|------|------|--------|--------|------|------|")

            for o in orders:
                lines.append(
                    f"| {o.order_id} | {o.code} | {o.name} | {o.trd_side} | "
                    f"{o.price:.3f} | {o.qty:.0f} | {o.filled_qty:.0f} | "
                    f"{o.filled_avg_price:.3f} | {o.status} | {o.create_time} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 查询订单失败: {e}"

    @server.tool()
    async def futu_get_history_orders(
        start: str = "",
        end: str = "",
        code: str = "",
        market: str | None = None,
    ) -> str:
        """Get historical order list.

        Args:
            start: Start date, e.g. "2024-01-01".
            end: End date, e.g. "2024-12-31".
            code: Filter by stock code.
            market: Market: HK, US, HKCC.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            orders = client.get_history_orders(market=mkt, start=start, end=end, code=code)

            if not orders:
                return "📋 无历史订单"

            lines = ["## 📋 历史订单\n"]
            lines.append("| 订单ID | 代码 | 名称 | 方向 | 价格 | 数量 | 已成交 | 成交价 | 状态 | 时间 |")
            lines.append("|--------|------|------|------|------|------|--------|--------|------|------|")

            for o in orders[-50:]:
                lines.append(
                    f"| {o.order_id} | {o.code} | {o.name} | {o.trd_side} | "
                    f"{o.price:.3f} | {o.qty:.0f} | {o.filled_qty:.0f} | "
                    f"{o.filled_avg_price:.3f} | {o.status} | {o.create_time} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 查询历史订单失败: {e}"

    @server.tool()
    async def futu_get_max_trade_qty(
        code: str,
        price: float,
        order_type: str = "NORMAL",
        market: str | None = None,
    ) -> str:
        """Query maximum buy/sell quantity for a stock at a given price.

        Args:
            code: Stock code, e.g. "HK.00700".
            price: Reference price.
            order_type: Order type: NORMAL, MARKET, etc.
            market: Market: HK, US, HKCC.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            result = client.get_max_trade_qty(code, price, order_type, market=mkt)

            return f"""## 📊 {code} 最大可交易数量 (价格: {price:.3f})

| 类型 | 数量 |
|------|------|
| 最大现金可买 | {result['max_cash_buy']:,} 股 |
| 最大融资可买 | {result['max_cash_and_margin_buy']:,} 股 |
| 最大可卖 | {result['max_position_sell']:,} 股 |"""
        except Exception as e:
            return f"❌ 查询最大可交易数量失败: {e}"
