"""Futu OpenD client wrapper — thin layer over futu-api SDK."""

from __future__ import annotations

import futu as ft
import pandas as pd

from .types import (
    AccountInfo,
    CapitalFlowData,
    FutuConfig,
    KLineData,
    MarketType,
    OrderBookData,
    OrderBookEntry,
    OrderData,
    PlateInfo,
    PositionData,
    QuoteData,
    SnapshotData,
    StockBasicInfo,
    TradingEnv,
)

# ---------------------------------------------------------------------------
# Market mapping helpers
# ---------------------------------------------------------------------------

_MARKET_MAP = {
    MarketType.HK: ft.Market.HK,
    MarketType.US: ft.Market.US,
    MarketType.SH: ft.Market.SH,
    MarketType.SZ: ft.Market.SZ,
}

_TRD_MKT_MAP = {
    MarketType.HK: ft.TrdMarket.HK,
    MarketType.US: ft.TrdMarket.US,
    MarketType.HKCC: ft.TrdMarket.HKCC,
}

_TRD_ENV_MAP = {
    TradingEnv.SIMULATE: ft.TrdEnv.SIMULATE,
    TradingEnv.REAL: ft.TrdEnv.REAL,
}

_KL_TYPE_MAP = {
    "K_1M": ft.KLType.K_1M,
    "K_3M": ft.KLType.K_3M,
    "K_5M": ft.KLType.K_5M,
    "K_15M": ft.KLType.K_15M,
    "K_30M": ft.KLType.K_30M,
    "K_60M": ft.KLType.K_60M,
    "K_DAY": ft.KLType.K_DAY,
    "K_WEEK": ft.KLType.K_WEEK,
    "K_MON": ft.KLType.K_MON,
    "K_QUARTER": ft.KLType.K_QUARTER,
    "K_YEAR": ft.KLType.K_YEAR,
}

_ORDER_TYPE_MAP = {
    "NORMAL": ft.OrderType.NORMAL,
    "MARKET": ft.OrderType.MARKET,
    "ABSOLUTE_LIMIT": ft.OrderType.ABSOLUTE_LIMIT,
    "AUCTION": ft.OrderType.AUCTION,
    "AUCTION_LIMIT": ft.OrderType.AUCTION_LIMIT,
    "SPECIAL_LIMIT": ft.OrderType.SPECIAL_LIMIT,
}

_TRD_SIDE_MAP = {
    "BUY": ft.TrdSide.BUY,
    "SELL": ft.TrdSide.SELL,
    "SELL_SHORT": ft.TrdSide.SELL_SHORT,
    "BUY_BACK": ft.TrdSide.BUY_BACK,
}


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


class FutuClient:
    """Wraps futu-api quote and trade contexts."""

    def __init__(self, config: FutuConfig) -> None:
        self._config = config
        self._quote_ctx: ft.OpenQuoteContext | None = None
        self._trade_ctxs: dict[str, ft.OpenSecTradeContext] = {}
        self._trade_unlocked = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def config(self) -> FutuConfig:
        return self._config

    def _get_quote_ctx(self) -> ft.OpenQuoteContext:
        if self._quote_ctx is None:
            self._quote_ctx = ft.OpenQuoteContext(
                host=self._config.host, port=self._config.port
            )
        return self._quote_ctx

    def _get_trade_ctx(self, market: MarketType | None = None) -> ft.OpenSecTradeContext:
        mkt = market or self._config.default_market
        key = mkt.value
        if key not in self._trade_ctxs:
            filter_mkt = _TRD_MKT_MAP.get(mkt, ft.TrdMarket.HK)
            self._trade_ctxs[key] = ft.OpenSecTradeContext(
                filter_trdmarket=filter_mkt,
                host=self._config.host,
                port=self._config.port,
            )
        return self._trade_ctxs[key]

    def close(self) -> None:
        if self._quote_ctx:
            self._quote_ctx.close()
            self._quote_ctx = None
        for ctx in self._trade_ctxs.values():
            ctx.close()
        self._trade_ctxs.clear()
        self._trade_unlocked = False

    # ------------------------------------------------------------------
    # Global state
    # ------------------------------------------------------------------

    def get_global_state(self) -> dict:
        ctx = self._get_quote_ctx()
        ret, data = ctx.get_global_state()
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_global_state failed: {data}")
        return {
            "market_hk": str(data.get("market_hk", "")),
            "market_us": str(data.get("market_us", "")),
            "market_sh": str(data.get("market_sh", "")),
            "market_sz": str(data.get("market_sz", "")),
            "server_ver": str(data.get("server_ver", "")),
            "program_status": str(data.get("program_status", "")),
        }

    # ------------------------------------------------------------------
    # Quote APIs
    # ------------------------------------------------------------------

    def get_stock_basicinfo(self, market: MarketType) -> list[StockBasicInfo]:
        ctx = self._get_quote_ctx()
        ft_market = _MARKET_MAP.get(market, ft.Market.HK)
        ret, data = ctx.get_stock_basicinfo(ft_market, stock_type=ft.SecurityType.STOCK)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_stock_basicinfo failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(StockBasicInfo(
                code=str(row["code"]),
                name=str(row.get("name", "")),
                lot_size=_safe_int(row.get("lot_size", 0)),
                stock_type=str(row.get("stock_type", "")),
                list_time=str(row.get("listing_date", "")),
                stock_id=_safe_int(row.get("stock_id", 0)),
            ))
        return result

    def get_market_snapshot(self, code_list: list[str]) -> list[SnapshotData]:
        ctx = self._get_quote_ctx()
        ret, data = ctx.get_market_snapshot(code_list)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_market_snapshot failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(SnapshotData(
                code=str(row["code"]),
                name=str(row.get("name", "")),
                last_price=_safe_float(row.get("last_price")),
                open_price=_safe_float(row.get("open_price")),
                high_price=_safe_float(row.get("high_price")),
                low_price=_safe_float(row.get("low_price")),
                prev_close=_safe_float(row.get("prev_close_price")),
                volume=_safe_int(row.get("volume")),
                turnover=_safe_float(row.get("turnover")),
                change_val=_safe_float(row.get("price_spread")),
                change_rate=_safe_float(row.get("change_rate")),
                market_val=_safe_float(row.get("market_val")),
                pe_ratio=_safe_float(row.get("pe_ttm_ratio")),
                pb_ratio=_safe_float(row.get("pb_ratio")),
                lot_size=_safe_int(row.get("lot_size")),
            ))
        return result

    def subscribe(self, code_list: list[str], subtype_list: list[str]) -> None:
        ctx = self._get_quote_ctx()
        ft_subtypes = []
        subtype_map = {
            "QUOTE": ft.SubType.QUOTE,
            "ORDER_BOOK": ft.SubType.ORDER_BOOK,
            "TICKER": ft.SubType.TICKER,
            "K_DAY": ft.SubType.K_DAY,
            "K_1M": ft.SubType.K_1M,
            "K_5M": ft.SubType.K_5M,
            "K_15M": ft.SubType.K_15M,
            "K_30M": ft.SubType.K_30M,
            "K_60M": ft.SubType.K_60M,
            "K_WEEK": ft.SubType.K_WEEK,
            "K_MON": ft.SubType.K_MON,
            "RT_DATA": ft.SubType.RT_DATA,
            "BROKER": ft.SubType.BROKER,
        }
        for st in subtype_list:
            if st in subtype_map:
                ft_subtypes.append(subtype_map[st])
        ret, msg = ctx.subscribe(code_list, ft_subtypes)
        if ret != ft.RET_OK:
            raise RuntimeError(f"subscribe failed: {msg}")

    def get_stock_quote(self, code_list: list[str]) -> list[QuoteData]:
        ctx = self._get_quote_ctx()
        # Subscribe first
        self.subscribe(code_list, ["QUOTE"])
        ret, data = ctx.get_stock_quote(code_list)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_stock_quote failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(QuoteData(
                code=str(row["code"]),
                name=str(row.get("name", "")),
                last_price=_safe_float(row.get("last_price")),
                open_price=_safe_float(row.get("open_price")),
                high_price=_safe_float(row.get("high_price")),
                low_price=_safe_float(row.get("low_price")),
                prev_close=_safe_float(row.get("prev_close_price")),
                volume=_safe_int(row.get("volume")),
                turnover=_safe_float(row.get("turnover")),
                change_val=_safe_float(row.get("price_spread")),
                change_rate=_safe_float(row.get("change_rate")),
                amplitude=_safe_float(row.get("amplitude")),
                timestamp=str(row.get("data_time", "")),
            ))
        return result

    def get_cur_kline(
        self, code: str, num: int = 100, ktype: str = "K_DAY"
    ) -> list[KLineData]:
        ctx = self._get_quote_ctx()
        ft_ktype = _KL_TYPE_MAP.get(ktype, ft.KLType.K_DAY)
        # Subscribe for the kline type
        subtype_map = {
            "K_DAY": "K_DAY", "K_1M": "K_1M", "K_5M": "K_5M",
            "K_15M": "K_15M", "K_30M": "K_30M", "K_60M": "K_60M",
            "K_WEEK": "K_WEEK", "K_MON": "K_MON",
        }
        sub_key = subtype_map.get(ktype, "K_DAY")
        self.subscribe([code], [sub_key])
        ret, data = ctx.get_cur_kline(code, num=num, ktype=ft_ktype)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_cur_kline failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(KLineData(
                code=str(row["code"]),
                time_key=str(row["time_key"]),
                open=_safe_float(row["open"]),
                close=_safe_float(row["close"]),
                high=_safe_float(row["high"]),
                low=_safe_float(row["low"]),
                volume=_safe_int(row["volume"]),
                turnover=_safe_float(row.get("turnover", 0)),
                change_rate=_safe_float(row.get("change_rate")),
            ))
        return result

    def request_history_kline(
        self,
        code: str,
        start: str | None = None,
        end: str | None = None,
        ktype: str = "K_DAY",
        max_count: int = 1000,
    ) -> list[KLineData]:
        ctx = self._get_quote_ctx()
        ft_ktype = _KL_TYPE_MAP.get(ktype, ft.KLType.K_DAY)
        ret, data, _ = ctx.request_history_kline(
            code, start=start, end=end, ktype=ft_ktype, max_count=max_count
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"request_history_kline failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(KLineData(
                code=str(row["code"]),
                time_key=str(row["time_key"]),
                open=_safe_float(row["open"]),
                close=_safe_float(row["close"]),
                high=_safe_float(row["high"]),
                low=_safe_float(row["low"]),
                volume=_safe_int(row["volume"]),
                turnover=_safe_float(row.get("turnover", 0)),
                change_rate=_safe_float(row.get("change_rate")),
            ))
        return result

    def get_order_book(self, code: str, num: int = 10) -> OrderBookData:
        ctx = self._get_quote_ctx()
        self.subscribe([code], ["ORDER_BOOK"])
        ret, data = ctx.get_order_book(code, num=num)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_order_book failed: {data}")
        bids = []
        asks = []
        for _, row in data.get("Bid", pd.DataFrame()).iterrows() if isinstance(data, dict) else []:
            bids.append(OrderBookEntry(
                price=_safe_float(row.get("price")),
                volume=_safe_int(row.get("volume")),
                order_num=_safe_int(row.get("order_num")),
            ))
        for _, row in data.get("Ask", pd.DataFrame()).iterrows() if isinstance(data, dict) else []:
            asks.append(OrderBookEntry(
                price=_safe_float(row.get("price")),
                volume=_safe_int(row.get("volume")),
                order_num=_safe_int(row.get("order_num")),
            ))
        return OrderBookData(code=code, bids=bids, asks=asks)

    def get_capital_flow(self, code: str) -> CapitalFlowData | None:
        ctx = self._get_quote_ctx()
        ret, data = ctx.get_capital_flow(code)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_capital_flow failed: {data}")
        if data.empty:
            return None
        row = data.iloc[-1]
        return CapitalFlowData(
            code=code,
            last_valid_time=str(row.get("last_valid_time", "")),
            super_in=_safe_float(row.get("super_in")),
            super_out=_safe_float(row.get("super_out")),
            big_in=_safe_float(row.get("big_in")),
            big_out=_safe_float(row.get("big_out")),
            mid_in=_safe_float(row.get("mid_in")),
            mid_out=_safe_float(row.get("mid_out")),
            small_in=_safe_float(row.get("small_in")),
            small_out=_safe_float(row.get("small_out")),
            net_inflow=(
                _safe_float(row.get("super_in")) - _safe_float(row.get("super_out"))
                + _safe_float(row.get("big_in")) - _safe_float(row.get("big_out"))
                + _safe_float(row.get("mid_in")) - _safe_float(row.get("mid_out"))
                + _safe_float(row.get("small_in")) - _safe_float(row.get("small_out"))
            ),
        )

    def get_capital_distribution(self, code: str) -> dict:
        ctx = self._get_quote_ctx()
        ret, data = ctx.get_capital_distribution(code)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_capital_distribution failed: {data}")
        if data.empty:
            return {}
        row = data.iloc[0]
        return {
            "capital_in_super": _safe_float(row.get("capital_in_super")),
            "capital_in_big": _safe_float(row.get("capital_in_big")),
            "capital_in_mid": _safe_float(row.get("capital_in_mid")),
            "capital_in_small": _safe_float(row.get("capital_in_small")),
            "capital_out_super": _safe_float(row.get("capital_out_super")),
            "capital_out_big": _safe_float(row.get("capital_out_big")),
            "capital_out_mid": _safe_float(row.get("capital_out_mid")),
            "capital_out_small": _safe_float(row.get("capital_out_small")),
        }

    def get_plate_list(self, market: MarketType, plate_class: str = "ALL") -> list[PlateInfo]:
        ctx = self._get_quote_ctx()
        ft_market = _MARKET_MAP.get(market, ft.Market.HK)
        plate_cls_map = {
            "ALL": ft.Plate.ALL,
            "INDUSTRY": ft.Plate.INDUSTRY,
            "REGION": ft.Plate.REGION,
            "CONCEPT": ft.Plate.CONCEPT,
        }
        ft_plate = plate_cls_map.get(plate_class, ft.Plate.ALL)
        ret, data = ctx.get_plate_list(ft_market, ft_plate)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_plate_list failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(PlateInfo(
                code=str(row["code"]),
                name=str(row.get("plate_name", "")),
                plate_type=str(row.get("plate_type", "")),
            ))
        return result

    def get_plate_stock(self, plate_code: str) -> list[dict]:
        ctx = self._get_quote_ctx()
        ret, data = ctx.get_plate_stock(plate_code)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_plate_stock failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append({
                "code": str(row["code"]),
                "name": str(row.get("stock_name", "")),
                "lot_size": _safe_int(row.get("lot_size")),
            })
        return result

    def stock_filter(
        self,
        market: MarketType,
        filter_list: list[dict] | None = None,
        begin: int = 0,
        num: int = 50,
    ) -> list[dict]:
        ctx = self._get_quote_ctx()
        ft_market = _MARKET_MAP.get(market, ft.Market.HK)
        # Build simple filters
        ft_filters = None
        if filter_list:
            ft_filters = []
            for f in filter_list:
                ft_filters.append(
                    ft.SimpleFilter(
                        stock_field=getattr(ft.StockField, f.get("field", "CUR_PRICE"), ft.StockField.CUR_PRICE),
                        filter_min=f.get("min"),
                        filter_max=f.get("max"),
                        is_no_filter=f.get("no_filter", False),
                    )
                )
        ret, data = ctx.get_stock_filter(
            ft_market, filter_list=ft_filters, begin=begin, num=num
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"stock_filter failed: {data}")
        result = []
        if isinstance(data, pd.DataFrame):
            for _, row in data.iterrows():
                result.append({
                    "code": str(row.get("code", "")),
                    "name": str(row.get("stock_name", "")),
                    "cur_price": _safe_float(row.get("cur_price")),
                    "change_rate": _safe_float(row.get("change_rate")),
                    "turnover": _safe_float(row.get("turnover")),
                    "volume": _safe_int(row.get("volume")),
                    "market_val": _safe_float(row.get("market_val")),
                })
        return result

    def set_price_reminder(
        self,
        code: str,
        op: str,
        key: int | None = None,
        reminder_type: str | None = None,
        reminder_freq: str | None = None,
        value: float | None = None,
        note: str | None = None,
    ) -> dict:
        ctx = self._get_quote_ctx()
        op_map = {
            "ADD": ft.SetPriceReminderOp.ADD,
            "DELETE": ft.SetPriceReminderOp.DEL,
            "ENABLE": ft.SetPriceReminderOp.ENABLE,
            "DISABLE": ft.SetPriceReminderOp.DISABLE,
            "MODIFY": ft.SetPriceReminderOp.MODIFY,
        }
        type_map = {
            "PRICE_UP": ft.PriceReminderType.PRICE_UP,
            "PRICE_DOWN": ft.PriceReminderType.PRICE_DOWN,
            "CHANGE_RATE_UP": ft.PriceReminderType.CHANGE_RATE_UP,
            "CHANGE_RATE_DOWN": ft.PriceReminderType.CHANGE_RATE_DOWN,
            "BID_PRICE_UP": ft.PriceReminderType.BID_PRICE_UP,
            "ASK_PRICE_DOWN": ft.PriceReminderType.ASK_PRICE_DOWN,
            "TURNOVER_UP": ft.PriceReminderType.TURNOVER_UP,
            "VOLUME_UP": ft.PriceReminderType.VOLUME_UP,
        }
        freq_map = {
            "ONCE": ft.PriceReminderFreq.ALWAYS,
            "ALWAYS": ft.PriceReminderFreq.ALWAYS,
        }
        ft_op = op_map.get(op, ft.SetPriceReminderOp.ADD)
        ft_type = type_map.get(reminder_type or "", None)
        ft_freq = freq_map.get(reminder_freq or "", None)
        ret, data = ctx.set_price_reminder(
            code, op=ft_op, key=key, reminder_type=ft_type,
            reminder_freq=ft_freq, value=value, note=note,
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"set_price_reminder failed: {data}")
        return {"key": data}

    def get_price_reminder(self, code: str | None = None, market: MarketType | None = None) -> list[dict]:
        ctx = self._get_quote_ctx()
        ft_market = _MARKET_MAP.get(market, None) if market else None
        ret, data = ctx.get_price_reminder(code=code, market=ft_market)
        if ret != ft.RET_OK:
            raise RuntimeError(f"get_price_reminder failed: {data}")
        result = []
        if isinstance(data, pd.DataFrame):
            for _, row in data.iterrows():
                result.append({
                    "code": str(row.get("code", "")),
                    "key": _safe_int(row.get("key")),
                    "reminder_type": str(row.get("reminder_type", "")),
                    "reminder_freq": str(row.get("reminder_freq", "")),
                    "value": _safe_float(row.get("value")),
                    "enable": bool(row.get("enable", False)),
                    "note": str(row.get("note", "")),
                })
        return result

    # ------------------------------------------------------------------
    # Trade APIs
    # ------------------------------------------------------------------

    def unlock_trade(self, password: str, market: MarketType | None = None) -> bool:
        ctx = self._get_trade_ctx(market)
        ret, data = ctx.unlock_trade(password)
        if ret != ft.RET_OK:
            raise RuntimeError(f"unlock_trade failed: {data}")
        self._trade_unlocked = True
        return True

    @property
    def is_trade_unlocked(self) -> bool:
        return self._trade_unlocked

    def get_account_info(
        self, market: MarketType | None = None, trd_env: TradingEnv | None = None
    ) -> AccountInfo:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.accinfo_query(trd_env=env)
        if ret != ft.RET_OK:
            raise RuntimeError(f"accinfo_query failed: {data}")
        row = data.iloc[0]
        return AccountInfo(
            acc_id=_safe_int(row.get("acc_id")),
            trd_env=str(trd_env or self._config.trd_env),
            power=_safe_float(row.get("power")),
            total_assets=_safe_float(row.get("total_assets")),
            cash=_safe_float(row.get("cash")),
            market_val=_safe_float(row.get("market_val")),
            frozen_cash=_safe_float(row.get("frozen_cash")),
            available_funds=_safe_float(row.get("avl_withdrawal_cash", row.get("power"))),
            currency=str(row.get("currency", "HKD")),
        )

    def get_positions(
        self, market: MarketType | None = None, trd_env: TradingEnv | None = None
    ) -> list[PositionData]:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.position_list_query(trd_env=env)
        if ret != ft.RET_OK:
            raise RuntimeError(f"position_list_query failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(PositionData(
                code=str(row["code"]),
                name=str(row.get("stock_name", "")),
                qty=_safe_float(row.get("qty")),
                can_sell_qty=_safe_float(row.get("can_sell_qty")),
                cost_price=_safe_float(row.get("cost_price")),
                market_val=_safe_float(row.get("market_val")),
                nominal_price=_safe_float(row.get("nominal_price")),
                pl_val=_safe_float(row.get("pl_val")),
                pl_ratio=_safe_float(row.get("pl_ratio")),
                today_pl_val=_safe_float(row.get("today_pl_val")),
            ))
        return result

    def place_order(
        self,
        code: str,
        price: float,
        qty: int,
        trd_side: str = "BUY",
        order_type: str = "NORMAL",
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
        adjust_limit: float = 0,
        remark: str = "",
    ) -> OrderData:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ft_side = _TRD_SIDE_MAP.get(trd_side, ft.TrdSide.BUY)
        ft_order_type = _ORDER_TYPE_MAP.get(order_type, ft.OrderType.NORMAL)
        ret, data = ctx.place_order(
            price=price,
            qty=qty,
            code=code,
            trd_side=ft_side,
            order_type=ft_order_type,
            trd_env=env,
            adjust_limit=adjust_limit,
            remark=remark,
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"place_order failed: {data}")
        row = data.iloc[0]
        return OrderData(
            order_id=str(row.get("order_id", "")),
            code=str(row.get("code", "")),
            name=str(row.get("stock_name", "")),
            trd_side=trd_side,
            order_type=order_type,
            qty=_safe_float(row.get("qty")),
            price=_safe_float(row.get("price")),
            status=str(row.get("order_status", "")),
            filled_qty=_safe_float(row.get("dealt_qty", 0)),
            filled_avg_price=_safe_float(row.get("dealt_avg_price", 0)),
            create_time=str(row.get("create_time", "")),
            updated_time=str(row.get("updated_time", "")),
        )

    def modify_order(
        self,
        order_id: str,
        price: float,
        qty: int,
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
    ) -> dict:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.modify_order(
            modify_order_op=ft.ModifyOrderOp.NORMAL,
            order_id=order_id,
            qty=qty,
            price=price,
            trd_env=env,
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"modify_order failed: {data}")
        return {"order_id": order_id, "new_price": price, "new_qty": qty}

    def cancel_order(
        self,
        order_id: str,
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
    ) -> dict:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.modify_order(
            modify_order_op=ft.ModifyOrderOp.CANCEL,
            order_id=order_id,
            qty=0,
            price=0,
            trd_env=env,
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"cancel_order failed: {data}")
        return {"order_id": order_id, "status": "cancelled"}

    def cancel_all_orders(
        self, market: MarketType | None = None, trd_env: TradingEnv | None = None
    ) -> dict:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.cancel_all_order(trd_env=env)
        if ret != ft.RET_OK:
            raise RuntimeError(f"cancel_all_order failed: {data}")
        return {"status": "all_cancelled"}

    def get_order_list(
        self,
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
        status_filter: list[str] | None = None,
    ) -> list[OrderData]:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ft_status = []
        if status_filter:
            status_map = {
                "SUBMITTED": ft.OrderStatus.SUBMITTED,
                "FILLED_ALL": ft.OrderStatus.FILLED_ALL,
                "FILLED_PART": ft.OrderStatus.FILLED_PART,
                "CANCELLED_ALL": ft.OrderStatus.CANCELLED_ALL,
                "FAILED": ft.OrderStatus.FAILED,
            }
            for s in status_filter:
                if s in status_map:
                    ft_status.append(status_map[s])
        ret, data = ctx.order_list_query(
            trd_env=env, status_filter_list=ft_status
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"order_list_query failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(OrderData(
                order_id=str(row.get("order_id", "")),
                code=str(row.get("code", "")),
                name=str(row.get("stock_name", "")),
                trd_side=str(row.get("trd_side", "")),
                order_type=str(row.get("order_type", "")),
                qty=_safe_float(row.get("qty")),
                price=_safe_float(row.get("price")),
                status=str(row.get("order_status", "")),
                filled_qty=_safe_float(row.get("dealt_qty", 0)),
                filled_avg_price=_safe_float(row.get("dealt_avg_price", 0)),
                create_time=str(row.get("create_time", "")),
                updated_time=str(row.get("updated_time", "")),
            ))
        return result

    def get_history_orders(
        self,
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
        start: str = "",
        end: str = "",
        code: str = "",
    ) -> list[OrderData]:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.history_order_list_query(
            trd_env=env, start=start, end=end, code=code
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"history_order_list_query failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append(OrderData(
                order_id=str(row.get("order_id", "")),
                code=str(row.get("code", "")),
                name=str(row.get("stock_name", "")),
                trd_side=str(row.get("trd_side", "")),
                order_type=str(row.get("order_type", "")),
                qty=_safe_float(row.get("qty")),
                price=_safe_float(row.get("price")),
                status=str(row.get("order_status", "")),
                filled_qty=_safe_float(row.get("dealt_qty", 0)),
                filled_avg_price=_safe_float(row.get("dealt_avg_price", 0)),
                create_time=str(row.get("create_time", "")),
                updated_time=str(row.get("updated_time", "")),
            ))
        return result

    def get_deal_list(
        self, market: MarketType | None = None, trd_env: TradingEnv | None = None
    ) -> list[dict]:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ret, data = ctx.deal_list_query(trd_env=env)
        if ret != ft.RET_OK:
            raise RuntimeError(f"deal_list_query failed: {data}")
        result = []
        for _, row in data.iterrows():
            result.append({
                "deal_id": str(row.get("deal_id", "")),
                "order_id": str(row.get("order_id", "")),
                "code": str(row.get("code", "")),
                "name": str(row.get("stock_name", "")),
                "trd_side": str(row.get("trd_side", "")),
                "qty": _safe_float(row.get("qty")),
                "price": _safe_float(row.get("price")),
                "create_time": str(row.get("create_time", "")),
            })
        return result

    def get_max_trade_qty(
        self,
        code: str,
        price: float,
        order_type: str = "NORMAL",
        market: MarketType | None = None,
        trd_env: TradingEnv | None = None,
    ) -> dict:
        ctx = self._get_trade_ctx(market)
        env = _TRD_ENV_MAP.get(trd_env or self._config.trd_env, ft.TrdEnv.SIMULATE)
        ft_order_type = _ORDER_TYPE_MAP.get(order_type, ft.OrderType.NORMAL)
        ret, data = ctx.acctradinginfo_query(
            order_type=ft_order_type, code=code, price=price, trd_env=env
        )
        if ret != ft.RET_OK:
            raise RuntimeError(f"acctradinginfo_query failed: {data}")
        row = data.iloc[0]
        return {
            "max_cash_buy": _safe_int(row.get("max_cash_buy")),
            "max_cash_and_margin_buy": _safe_int(row.get("max_cash_and_margin_buy")),
            "max_position_sell": _safe_int(row.get("max_position_sell")),
        }
