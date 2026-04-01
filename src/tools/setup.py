"""Setup & configuration tools — OpenD connection and trade unlock."""

from __future__ import annotations

from mcp.server import Server

from ..storage.db import get_config, set_config
from ..futu_client import FutuClient, FutuConfig, TradingEnv


def _get_client() -> FutuClient:
    host = get_config("futu_host") or "127.0.0.1"
    port = int(get_config("futu_port") or "11111")
    trd_env_str = get_config("futu_trd_env") or "SIMULATE"
    trd_env = TradingEnv(trd_env_str) if trd_env_str in ("SIMULATE", "REAL") else TradingEnv.SIMULATE
    default_market_str = get_config("futu_default_market") or "HK"
    from ..futu_client.types import MarketType
    default_market = MarketType(default_market_str) if default_market_str in ("HK", "US", "SH", "SZ", "HKCC") else MarketType.HK
    return FutuClient(FutuConfig(host=host, port=port, trd_env=trd_env, default_market=default_market))


# Shared client instance — lazily created
_client: FutuClient | None = None


def get_shared_client() -> FutuClient:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def reset_shared_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def register_setup_tools(server: Server) -> None:
    @server.tool()
    async def futu_setup_guide(step: int | None = None) -> str:
        """Get step-by-step guide for Futu OpenD setup and connection configuration.

        Args:
            step: Specific step number (1-5) to show, omit for overview.
        """
        steps = {
            1: """## Step 1: 注册富途账户

1. 前往 **https://www.futunn.com** 注册账户
2. 完成实名认证（需身份证/护照）
3. 开通证券交易权限（港股、美股等）
4. 开通 OpenAPI 权限：登录富途牛牛 → 个人中心 → API管理

> 💡 富途提供**模拟盘**功能，注册后即可使用，无需入金！""",

            2: """## Step 2: 安装 OpenD 网关

1. 下载 OpenD: **https://www.futunn.com/download/openAPI**
2. 选择你的系统版本（Mac/Windows/Linux）
3. 可选：可视化版（GUI）适合入门，命令行版适合服务器部署
4. 安装并启动 OpenD
5. 首次启动需要用富途账号登录

> ⚠️ OpenD 必须在本地运行，API 通过 TCP 连接 OpenD 网关。""",

            3: """## Step 3: 配置连接

使用 **futu_configure** 工具配置连接参数：
- `host`: OpenD 网关地址（默认 127.0.0.1）
- `port`: OpenD 网关端口（默认 11111）
- `trd_env`: 交易环境 "SIMULATE"（模拟盘）或 "REAL"（实盘）
- `default_market`: 默认市场 "HK" / "US" / "SH" / "SZ"

> 🔒 配置信息保存在本地 SQLite 数据库中。""",

            4: """## Step 4: 验证连接

配置完成后，我会调用 **futu_get_global_state** 验证：
- ✅ OpenD 网关连接正常
- ✅ 各市场状态（港股、美股、A股）
- ✅ 服务器版本信息

如果连接失败，请检查：
1. OpenD 是否已启动
2. 端口号是否正确（默认 11111）
3. 防火墙是否阻止了连接""",

            5: """## Step 5: 解锁交易 & 开始使用！

交易前需要解锁（每次会话）：
- 调用 **futu_unlock_trade** 输入交易密码

解锁后你可以：
- 📊 **查看行情**: 实时报价、K线、买卖盘、资金流向
- 💰 **下单交易**: 港股、美股、A股（沪港通/深港通）
- 📋 **创建策略**: 定义自动交易策略
- 🔔 **设置告警**: 到价提醒、持仓监控
- 📈 **回测**: 用历史数据验证策略
- 📝 **复盘**: 绩效分析和交易日志

> 💡 强烈建议先用**模拟盘**熟悉系统，再切换到实盘。""",
        }

        if step and step in steps:
            return steps[step]

        configured = get_config("futu_host") is not None
        verified = get_config("futu_verified") == "true"

        overview = f"""# 📈 富途多市场股票交易 — 设置指南

## 快速开始 (5 步)

| 步骤 | 操作 | 状态 |
|------|------|------|
| 1 | 注册富途账户 | {"✅" if configured else "⬜"} |
| 2 | 安装 OpenD 网关 | {"✅" if configured else "⬜"} |
| 3 | 配置连接参数 | {"✅" if configured else "⬜"} |
| 4 | 验证连接 | {"✅" if verified else "⬜"} |
| 5 | 解锁交易 & 开始！ | ⬜ |

输入步骤编号查看详情，例如 "显示步骤 2"。

---
**当前配置**: {f'Host = {get_config("futu_host")}:{get_config("futu_port")}, 环境 = {get_config("futu_trd_env") or "SIMULATE"}, 市场 = {get_config("futu_default_market") or "HK"}' if configured else '尚未配置'}"""

        return overview

    @server.tool()
    async def futu_configure(
        host: str = "127.0.0.1",
        port: int = 11111,
        trd_env: str = "SIMULATE",
        default_market: str = "HK",
    ) -> str:
        """Configure Futu OpenD connection and trading environment.

        Args:
            host: OpenD gateway host address (default 127.0.0.1).
            port: OpenD gateway port (default 11111).
            trd_env: Trading environment: SIMULATE (paper) or REAL (live).
            default_market: Default market: HK, US, SH, SZ, HKCC.
        """
        # Validate trd_env
        if trd_env not in ("SIMULATE", "REAL"):
            return "❌ trd_env must be 'SIMULATE' or 'REAL'"
        if default_market not in ("HK", "US", "SH", "SZ", "HKCC"):
            return "❌ default_market must be one of: HK, US, SH, SZ, HKCC"

        # Save config
        set_config("futu_host", host)
        set_config("futu_port", str(port))
        set_config("futu_trd_env", trd_env)
        set_config("futu_default_market", default_market)

        # Reset client to pick up new config
        reset_shared_client()

        # Try to connect
        try:
            client = get_shared_client()
            state = client.get_global_state()
            set_config("futu_verified", "true")

            env_warning = (
                "\n\n⚠️ **警告：你当前处于实盘模式，交易将使用真实资金！**"
                if trd_env == "REAL"
                else "\n\n✅ **模拟盘模式** — 不涉及真实资金。"
            )

            return f"""## ✅ 配置成功！

**OpenD 地址**: {host}:{port}
**交易环境**: {trd_env}
**默认市场**: {default_market}
**服务器版本**: {state.get('server_ver', 'N/A')}
**港股市场状态**: {state.get('market_hk', 'N/A')}
**美股市场状态**: {state.get('market_us', 'N/A')}
**沪市状态**: {state.get('market_sh', 'N/A')}
**深市状态**: {state.get('market_sz', 'N/A')}{env_warning}"""

        except Exception as e:
            set_config("futu_verified", "false")
            reset_shared_client()
            return f"""## ❌ 连接失败

无法连接到 OpenD 网关。错误: {e}

请检查：
1. OpenD 是否已启动并登录
2. 地址和端口是否正确 ({host}:{port})
3. 防火墙设置

使用 **futu_setup_guide** 步骤 2 查看 OpenD 安装说明。"""

    @server.tool()
    async def futu_get_global_state() -> str:
        """Check OpenD gateway connection status and market states."""
        try:
            client = get_shared_client()
            state = client.get_global_state()
            return f"""## 🌐 OpenD 网关状态

| 项目 | 状态 |
|------|------|
| 服务器版本 | {state.get('server_ver', 'N/A')} |
| 程序状态 | {state.get('program_status', 'N/A')} |
| 港股市场 | {state.get('market_hk', 'N/A')} |
| 美股市场 | {state.get('market_us', 'N/A')} |
| 沪市 | {state.get('market_sh', 'N/A')} |
| 深市 | {state.get('market_sz', 'N/A')} |

**交易环境**: {get_config('futu_trd_env') or 'SIMULATE'}
**默认市场**: {get_config('futu_default_market') or 'HK'}"""
        except Exception as e:
            return f"❌ 无法连接 OpenD 网关: {e}\n\n请确认 OpenD 已启动并运行。"

    @server.tool()
    async def futu_unlock_trade(password: str, market: str | None = None) -> str:
        """Unlock trade for the current session. Required before placing orders.

        Args:
            password: Trade unlock password (NOT your login password).
            market: Market to unlock for: HK, US, HKCC. Omit for default.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ", "HKCC") else None
            client.unlock_trade(password, market=mkt)
            env = get_config("futu_trd_env") or "SIMULATE"
            env_label = "🟢 模拟盘" if env == "SIMULATE" else "🔴 实盘"
            return f"""## 🔓 交易已解锁

**交易环境**: {env_label}
**市场**: {market or get_config('futu_default_market') or 'HK'}

现在可以下单交易了。"""
        except Exception as e:
            return f"❌ 交易解锁失败: {e}\n\n请检查交易密码是否正确。"
