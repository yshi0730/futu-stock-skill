# USER.md - How to Use This Agent

## What I Can Do

I'm your personal multi-market stock trading advisor. I connect to Futu OpenAPI and handle everything from market research to live order execution across Hong Kong, US, and A-share markets.

### Core Capabilities

- **Market Research** — Real-time quotes, K-lines, order book, broker queue, capital flow analysis, stock screening, sector analysis
- **Trading** — Place limit/market/stop/enhanced-limit orders across HK, US, A-share markets, manage positions
- **Strategy Building** — Create custom trading strategies using built-in templates (SMA crossover, DCA, mean reversion, momentum, trailing stop)
- **Backtesting** — Test strategies against historical data with full performance metrics (Sharpe ratio, max drawdown, win rate)
- **Monitoring** — Real-time price alerts, periodic position tracking, automated notifications
- **Portfolio Review** — Performance reports, trade journal, review sessions with actionable insights
- **Multi-Market** — Seamlessly trade across HK (港股), US (美股), and A-shares (A股) from one interface

## Getting Started

1. **Install OpenD** — Download from https://www.futunn.com/download/openAPI and start the gateway
2. **First time?** Just say hi — I'll walk you through configuring the connection and unlocking trade access
3. **Start with paper trading** — I strongly recommend practicing with virtual money first (模拟盘)

## Example Interactions

- "今天大盘怎么样？"
- "看一下腾讯的K线图"
- "查看 NVDA 的实时报价和资金流向"
- "买入 1000 股 00700.HK，限价 380"
- "创建一个 VOO 定投策略，每周 $500"
- "回测我的动量策略，2024-01-01 到 2025-01-01"
- "设置告警：如果特斯拉跌破 $200 通知我"
- "这个月的投资组合表现怎么样？"
- "复盘上周的交易"

## Requirements

- Futu OpenD gateway running locally (download from https://www.futunn.com/download/openAPI)
- A Futu (富途) account with OpenAPI access enabled
- Python 3.10+ and `futu-api` package
