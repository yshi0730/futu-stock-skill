# USER.md - How to Use This Agent

## What I Can Do

I'm your autonomous multi-market trading agent. I connect to Futu OpenAPI and actively manage your portfolio — from research and execution to rebalancing and overnight analysis across Hong Kong, US, and A-share markets. I don't just discuss trades; I execute them.

### Core Capabilities

- **Autonomous Trading** — Execute trades automatically per your authorization level (Advisory / Semi-Auto / Full Auto) with built-in guardrails and daily loss circuit breakers
- **Market Research** — Real-time quotes, K-lines, order book, broker queue, capital flow analysis, stock screening, sector analysis
- **Trading** — Place limit/market/stop/enhanced-limit orders across HK, US, A-share markets, manage positions
- **Strategy Building** — Create custom trading strategies using built-in templates (SMA crossover, DCA, mean reversion, momentum, trailing stop)
- **Backtesting** — Test strategies against historical data with full performance metrics (Sharpe ratio, max drawdown, win rate)
- **Monitoring** — Real-time price alerts, periodic position tracking, automated notifications
- **Visual Dashboard** — Build and serve a live dashboard to monitor positions, P&L, alerts, and strategy performance at a glance
- **Overnight Research** — Run analysis and screening jobs overnight so actionable ideas are ready before the market opens
- **Portfolio Review** — Performance reports, trade journal, review sessions with actionable insights
- **Multi-Market** — Seamlessly trade across HK (港股), US (美股), and A-shares (A股) from one interface

## Getting Started

1. **Install OpenD** — Download from https://www.futunn.com/download/openAPI and start the gateway
2. **First time?** Just say hi — I'll walk you through configuring the connection and unlocking trade access
3. **Start with paper trading** — I strongly recommend practicing with virtual money first (模拟盘)

## Example Interactions

- "帮我建 dashboard" — Build a live visual dashboard for your portfolio
- "帮我建一个定投策略" — Create an automated DCA strategy and start executing
- "今天大盘怎么样？"
- "看一下腾讯的K线图"
- "查看 NVDA 的实时报价和资金流向"
- "买入 1000 股 00700.HK，限价 380"
- "创建一个 VOO 定投策略，每周 $500"
- "把我的美股组合设成 Semi-Auto 模式"
- "回测我的动量策略，2024-01-01 到 2025-01-01"
- "设置告警：如果特斯拉跌破 $200 通知我"
- "今晚帮我研究一下半导体板块" — Overnight research, results ready by morning
- "这个月的投资组合表现怎么样？"
- "复盘上周的交易"

## Requirements

- Futu OpenD gateway running locally (download from https://www.futunn.com/download/openAPI)
- A Futu (富途) account with OpenAPI access enabled
- Python 3.10+ and `futu-api` package
