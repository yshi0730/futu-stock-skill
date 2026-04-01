from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MarketType(str, Enum):
    HK = "HK"
    US = "US"
    SH = "SH"
    SZ = "SZ"
    HKCC = "HKCC"  # A-shares via Stock Connect


class TradingEnv(str, Enum):
    SIMULATE = "SIMULATE"
    REAL = "REAL"


@dataclass
class FutuConfig:
    host: str = "127.0.0.1"
    port: int = 11111
    trd_env: TradingEnv = TradingEnv.SIMULATE
    default_market: MarketType = MarketType.HK


@dataclass
class QuoteData:
    code: str
    name: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    volume: int
    turnover: float
    change_val: float
    change_rate: float
    amplitude: float
    timestamp: str


@dataclass
class OrderBookEntry:
    price: float
    volume: int
    order_num: int


@dataclass
class OrderBookData:
    code: str
    bids: list[OrderBookEntry] = field(default_factory=list)
    asks: list[OrderBookEntry] = field(default_factory=list)


@dataclass
class KLineData:
    code: str
    time_key: str
    open: float
    close: float
    high: float
    low: float
    volume: int
    turnover: float
    change_rate: float | None = None


@dataclass
class AccountInfo:
    acc_id: int
    trd_env: str
    power: float  # buying power
    total_assets: float
    cash: float
    market_val: float
    frozen_cash: float
    available_funds: float
    currency: str


@dataclass
class PositionData:
    code: str
    name: str
    qty: float
    can_sell_qty: float
    cost_price: float
    market_val: float
    nominal_price: float
    pl_val: float
    pl_ratio: float
    today_pl_val: float


@dataclass
class OrderData:
    order_id: str
    code: str
    name: str
    trd_side: str
    order_type: str
    qty: float
    price: float
    status: str
    filled_qty: float
    filled_avg_price: float
    create_time: str
    updated_time: str


@dataclass
class SnapshotData:
    code: str
    name: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    volume: int
    turnover: float
    change_val: float
    change_rate: float
    market_val: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    lot_size: int | None = None


@dataclass
class CapitalFlowData:
    code: str
    last_valid_time: str
    super_in: float  # 特大单流入
    super_out: float
    big_in: float  # 大单流入
    big_out: float
    mid_in: float  # 中单流入
    mid_out: float
    small_in: float  # 小单流入
    small_out: float
    net_inflow: float  # 净流入


@dataclass
class PlateInfo:
    code: str
    name: str
    plate_type: str


@dataclass
class StockBasicInfo:
    code: str
    name: str
    lot_size: int
    stock_type: str
    list_time: str
    stock_id: int
    main_contract: bool = False
    last_trade_time: str = ""
