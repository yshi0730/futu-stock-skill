"""Market data tools — quotes, K-lines, order book, capital flow, screening."""

from __future__ import annotations

from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_config


def register_market_data_tools(server: Server) -> None:
    @server.tool()
    async def futu_get_quote(codes: str) -> str:
        """Get real-time quotes for one or more stocks.

        Args:
            codes: Comma-separated stock codes, e.g. "HK.00700,US.AAPL".
        """
        try:
            client = get_shared_client()
            code_list = [c.strip() for c in codes.split(",")]
            quotes = client.get_stock_quote(code_list)

            lines = ["## 📊 实时报价\n"]
            for q in quotes:
                chg_emoji = "🟢" if q.change_rate >= 0 else "🔴"
                lines.append(f"""### {q.name} ({q.code})
| 项目 | 数值 |
|------|------|
| 最新价 | {q.last_price:.3f} |
| 涨跌额 | {chg_emoji} {q.change_val:+.3f} |
| 涨跌幅 | {chg_emoji} {q.change_rate:+.2f}% |
| 开盘价 | {q.open_price:.3f} |
| 最高价 | {q.high_price:.3f} |
| 最低价 | {q.low_price:.3f} |
| 昨收 | {q.prev_close:.3f} |
| 成交量 | {q.volume:,} |
| 成交额 | {q.turnover:,.2f} |
| 振幅 | {q.amplitude:.2f}% |
| 时间 | {q.timestamp} |
""")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取报价失败: {e}"

    @server.tool()
    async def futu_get_snapshot(codes: str) -> str:
        """Get market snapshots for multiple stocks — good for quick comparison.

        Args:
            codes: Comma-separated stock codes, e.g. "HK.00700,HK.09988,HK.03690".
        """
        try:
            client = get_shared_client()
            code_list = [c.strip() for c in codes.split(",")]
            snapshots = client.get_market_snapshot(code_list)

            lines = ["## 📸 市场快照\n"]
            lines.append("| 代码 | 名称 | 现价 | 涨跌% | 成交量 | 成交额 | 市值 | PE | PB | 每手 |")
            lines.append("|------|------|------|-------|--------|--------|------|----|----|------|")

            for s in snapshots:
                chg_emoji = "🟢" if s.change_rate >= 0 else "🔴"
                mv = f"{s.market_val / 1e8:,.1f}亿" if s.market_val else "N/A"
                pe = f"{s.pe_ratio:.1f}" if s.pe_ratio else "N/A"
                pb = f"{s.pb_ratio:.2f}" if s.pb_ratio else "N/A"
                lines.append(
                    f"| {s.code} | {s.name} | {s.last_price:.3f} | "
                    f"{chg_emoji} {s.change_rate:+.2f}% | {s.volume:,} | "
                    f"{s.turnover / 1e4:,.0f}万 | {mv} | {pe} | {pb} | {s.lot_size or 'N/A'} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取快照失败: {e}"

    @server.tool()
    async def futu_get_kline(
        code: str,
        ktype: str = "K_DAY",
        num: int = 60,
    ) -> str:
        """Get K-line (candlestick) data for a stock.

        Args:
            code: Stock code, e.g. "HK.00700".
            ktype: K-line type: K_1M, K_5M, K_15M, K_30M, K_60M, K_DAY, K_WEEK, K_MON.
            num: Number of K-line bars (default 60, max 1000).
        """
        try:
            client = get_shared_client()
            klines = client.get_cur_kline(code, num=min(num, 1000), ktype=ktype)

            if not klines:
                return f"📊 {code} 无K线数据"

            lines = [f"## 📊 {code} K线 ({ktype}, 最近{len(klines)}根)\n"]
            lines.append("| 时间 | 开 | 高 | 低 | 收 | 成交量 | 涨跌% |")
            lines.append("|------|-----|-----|-----|-----|--------|-------|")

            for k in klines[-30:]:  # Show last 30 bars
                chg = f"{k.change_rate:+.2f}%" if k.change_rate is not None else "N/A"
                lines.append(
                    f"| {k.time_key} | {k.open:.3f} | {k.high:.3f} | "
                    f"{k.low:.3f} | {k.close:.3f} | {k.volume:,} | {chg} |"
                )

            if len(klines) > 30:
                lines.append(f"\n*显示最近30根，共{len(klines)}根数据*")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取K线失败: {e}"

    @server.tool()
    async def futu_get_history_kline(
        code: str,
        start: str,
        end: str,
        ktype: str = "K_DAY",
        max_count: int = 500,
    ) -> str:
        """Get historical K-line data for a date range.

        Args:
            code: Stock code, e.g. "HK.00700".
            start: Start date, e.g. "2024-01-01".
            end: End date, e.g. "2024-12-31".
            ktype: K-line type: K_DAY, K_WEEK, K_MON.
            max_count: Max number of bars (default 500).
        """
        try:
            client = get_shared_client()
            klines = client.request_history_kline(
                code, start=start, end=end, ktype=ktype, max_count=max_count
            )

            if not klines:
                return f"📊 {code} 在 {start} ~ {end} 期间无K线数据"

            lines = [f"## 📊 {code} 历史K线 ({ktype}, {start} ~ {end})\n"]
            lines.append(f"**数据量**: {len(klines)} 根\n")
            lines.append("| 时间 | 开 | 高 | 低 | 收 | 成交量 | 涨跌% |")
            lines.append("|------|-----|-----|-----|-----|--------|-------|")

            display = klines[-50:]  # Show last 50
            for k in display:
                chg = f"{k.change_rate:+.2f}%" if k.change_rate is not None else "N/A"
                lines.append(
                    f"| {k.time_key} | {k.open:.3f} | {k.high:.3f} | "
                    f"{k.low:.3f} | {k.close:.3f} | {k.volume:,} | {chg} |"
                )

            if len(klines) > 50:
                lines.append(f"\n*显示最近50根，共{len(klines)}根数据*")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取历史K线失败: {e}"

    @server.tool()
    async def futu_get_orderbook(code: str, num: int = 10) -> str:
        """Get order book (bid/ask depth) for a stock.

        Args:
            code: Stock code, e.g. "HK.00700".
            num: Number of price levels (default 10).
        """
        try:
            client = get_shared_client()
            ob = client.get_order_book(code, num=num)

            lines = [f"## 📖 {code} 买卖盘\n"]
            lines.append("### 卖盘 (Ask)")
            lines.append("| 价格 | 数量 | 订单数 |")
            lines.append("|------|------|--------|")
            for a in reversed(ob.asks[:num]):
                lines.append(f"| {a.price:.3f} | {a.volume:,} | {a.order_num} |")

            lines.append("\n### 买盘 (Bid)")
            lines.append("| 价格 | 数量 | 订单数 |")
            lines.append("|------|------|--------|")
            for b in ob.bids[:num]:
                lines.append(f"| {b.price:.3f} | {b.volume:,} | {b.order_num} |")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取买卖盘失败: {e}"

    @server.tool()
    async def futu_get_capital_flow(code: str) -> str:
        """Get capital flow analysis for a stock — shows institutional money movement.

        Args:
            code: Stock code, e.g. "HK.00700".
        """
        try:
            client = get_shared_client()
            flow = client.get_capital_flow(code)

            if not flow:
                return f"📊 {code} 无资金流向数据"

            net_emoji = "🟢" if flow.net_inflow >= 0 else "🔴"

            return f"""## 💰 {code} 资金流向

**最后更新**: {flow.last_valid_time}

| 类型 | 流入 | 流出 | 净额 |
|------|------|------|------|
| 特大单 | {flow.super_in / 1e4:,.0f}万 | {flow.super_out / 1e4:,.0f}万 | {(flow.super_in - flow.super_out) / 1e4:,.0f}万 |
| 大单 | {flow.big_in / 1e4:,.0f}万 | {flow.big_out / 1e4:,.0f}万 | {(flow.big_in - flow.big_out) / 1e4:,.0f}万 |
| 中单 | {flow.mid_in / 1e4:,.0f}万 | {flow.mid_out / 1e4:,.0f}万 | {(flow.mid_in - flow.mid_out) / 1e4:,.0f}万 |
| 小单 | {flow.small_in / 1e4:,.0f}万 | {flow.small_out / 1e4:,.0f}万 | {(flow.small_in - flow.small_out) / 1e4:,.0f}万 |

**净流入**: {net_emoji} {flow.net_inflow / 1e4:,.0f}万"""
        except Exception as e:
            return f"❌ 获取资金流向失败: {e}"

    @server.tool()
    async def futu_market_overview() -> str:
        """Get market overview across HK, US, and A-share markets."""
        try:
            client = get_shared_client()
            # Key indices
            indices = [
                "HK.800000",   # HSI 恒生指数
                "HK.800700",   # HSI Tech 恒生科技
                "US.DJI",      # Dow Jones
                "US.IXIC",     # Nasdaq
                "US.SPX",      # S&P 500
                "SH.000001",   # 上证指数
                "SZ.399001",   # 深证成指
                "SZ.399006",   # 创业板指
            ]
            snapshots = client.get_market_snapshot(indices)

            lines = ["## 🌍 市场概览\n"]
            lines.append("| 指数 | 名称 | 现价 | 涨跌% | 成交额 |")
            lines.append("|------|------|------|-------|--------|")

            for s in snapshots:
                chg_emoji = "🟢" if s.change_rate >= 0 else "🔴"
                turnover = f"{s.turnover / 1e8:,.1f}亿" if s.turnover else "N/A"
                lines.append(
                    f"| {s.code} | {s.name} | {s.last_price:,.2f} | "
                    f"{chg_emoji} {s.change_rate:+.2f}% | {turnover} |"
                )

            env = get_config("futu_trd_env") or "SIMULATE"
            env_label = "🟢 模拟盘" if env == "SIMULATE" else "🔴 实盘"
            lines.append(f"\n**交易环境**: {env_label}")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取市场概览失败: {e}"

    @server.tool()
    async def futu_stock_filter(
        market: str = "HK",
        min_price: float | None = None,
        max_price: float | None = None,
        min_change_rate: float | None = None,
        max_change_rate: float | None = None,
        min_market_val: float | None = None,
        num: int = 30,
    ) -> str:
        """Screen stocks by price, change rate, market cap, etc.

        Args:
            market: Market to screen: HK, US, SH, SZ.
            min_price: Minimum current price.
            max_price: Maximum current price.
            min_change_rate: Minimum change rate (%).
            max_change_rate: Maximum change rate (%).
            min_market_val: Minimum market value.
            num: Number of results (default 30).
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market in ("HK", "US", "SH", "SZ") else MarketType.HK

            filters = []
            if min_price is not None or max_price is not None:
                filters.append({"field": "CUR_PRICE", "min": min_price, "max": max_price})
            if min_change_rate is not None or max_change_rate is not None:
                filters.append({"field": "CHANGE_RATE", "min": min_change_rate, "max": max_change_rate})
            if min_market_val is not None:
                filters.append({"field": "MARKET_VAL", "min": min_market_val})

            results = client.stock_filter(mkt, filter_list=filters or None, num=num)

            if not results:
                return f"📊 {market} 市场无符合条件的股票"

            lines = [f"## 🔍 选股结果 ({market}市场)\n"]
            lines.append("| 代码 | 名称 | 现价 | 涨跌% | 成交额 | 市值 |")
            lines.append("|------|------|------|-------|--------|------|")

            for r in results:
                mv = f"{r['market_val'] / 1e8:,.1f}亿" if r.get("market_val") else "N/A"
                turnover = f"{r['turnover'] / 1e4:,.0f}万" if r.get("turnover") else "N/A"
                lines.append(
                    f"| {r['code']} | {r['name']} | {r['cur_price']:.3f} | "
                    f"{r['change_rate']:+.2f}% | {turnover} | {mv} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 选股失败: {e}"

    @server.tool()
    async def futu_get_plate_list(market: str = "HK", plate_class: str = "ALL") -> str:
        """Get sector/plate list for a market.

        Args:
            market: Market: HK, US, SH, SZ.
            plate_class: Plate class: ALL, INDUSTRY, REGION, CONCEPT.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market in ("HK", "US", "SH", "SZ") else MarketType.HK
            plates = client.get_plate_list(mkt, plate_class)

            if not plates:
                return f"📊 {market} 市场无板块数据"

            lines = [f"## 📊 板块列表 ({market}, {plate_class})\n"]
            lines.append("| 代码 | 名称 | 类型 |")
            lines.append("|------|------|------|")

            for p in plates[:50]:
                lines.append(f"| {p.code} | {p.name} | {p.plate_type} |")

            if len(plates) > 50:
                lines.append(f"\n*显示前50个，共{len(plates)}个板块*")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取板块列表失败: {e}"
