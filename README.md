# Futu Stock Trading Skill

Professional multi-market stock trading skill for OpenClaw, powered by [Futu OpenAPI](https://openapi.futunn.com/futu-api-doc/).

## Supported Markets

- **Hong Kong** (港股) — HK.00700, HK.09988, etc.
- **US Stocks** (美股) — US.AAPL, US.TSLA, etc.
- **A-Shares** (A股) — SH.600519, SZ.000001, etc. (via Stock Connect)
- **Futures** (期货) — coming soon

## Features

- Real-time quotes, K-lines, order book, broker queue
- Capital flow & distribution analysis
- Stock screening & sector analysis
- Order placement, modification, cancellation
- Paper trading (模拟盘) support
- Strategy building with templates (SMA crossover, DCA, mean reversion, momentum)
- Backtesting with performance metrics
- Native price reminders via OpenD
- Trade journal & performance review

## Prerequisites

1. [Futu account](https://www.futunn.com) with OpenAPI access
2. [Futu OpenD](https://www.futunn.com/download/openAPI) gateway running locally
3. Python 3.10+

## Setup

```bash
pip install -e .
```

## Usage

```bash
# Start MCP server (stdio transport)
futu-skill

# Or run directly
python -m src.server
```

## Configuration

The skill auto-configures via the `futu_configure` tool. You can also set environment variables:

```bash
export FUTU_OPEND_HOST=127.0.0.1
export FUTU_OPEND_PORT=11111
export FUTU_TRD_ENV=SIMULATE
export FUTU_DEFAULT_MARKET=HK
```
