#!/usr/bin/env python3
"""Futu Stock Trading MCP Server — stdio transport."""

from __future__ import annotations

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .tools.setup import register_setup_tools
from .tools.account import register_account_tools
from .tools.market_data import register_market_data_tools
from .tools.trading import register_trading_tools
from .tools.strategy import register_strategy_tools
from .tools.monitor import register_monitor_tools
from .tools.backtest import register_backtest_tools
from .tools.analytics import register_analytics_tools


def create_server() -> Server:
    server = Server("futu-stock")

    # Register all tool groups
    register_setup_tools(server)
    register_account_tools(server)
    register_market_data_tools(server)
    register_trading_tools(server)
    register_strategy_tools(server)
    register_monitor_tools(server)
    register_backtest_tools(server)
    register_analytics_tools(server)

    return server


async def amain() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
