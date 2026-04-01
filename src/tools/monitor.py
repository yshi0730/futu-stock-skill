"""Monitor tools — price reminders and alert management."""

from __future__ import annotations

from mcp.server import Server

from .setup import get_shared_client
from ..storage.db import get_config


def register_monitor_tools(server: Server) -> None:
    @server.tool()
    async def futu_set_price_reminder(
        code: str,
        reminder_type: str,
        value: float,
        note: str = "",
    ) -> str:
        """Set a price reminder (native Futu alert).

        Args:
            code: Stock code, e.g. "HK.00700".
            reminder_type: PRICE_UP, PRICE_DOWN, CHANGE_RATE_UP, CHANGE_RATE_DOWN, TURNOVER_UP, VOLUME_UP.
            value: Trigger value (price for PRICE_*, percentage for CHANGE_RATE_*, amount for TURNOVER/VOLUME).
            note: Optional note for the reminder.
        """
        try:
            client = get_shared_client()
            result = client.set_price_reminder(
                code, op="ADD", reminder_type=reminder_type, value=value, note=note
            )
            return f"""## 🔔 到价提醒已设置

**股票**: {code}
**类型**: {reminder_type}
**触发值**: {value}
**备注**: {note or '—'}
**提醒ID**: {result.get('key', 'N/A')}"""
        except Exception as e:
            return f"❌ 设置到价提醒失败: {e}"

    @server.tool()
    async def futu_get_price_reminders(code: str | None = None, market: str | None = None) -> str:
        """Get all price reminders, optionally filtered by stock or market.

        Args:
            code: Filter by stock code.
            market: Filter by market: HK, US, SH, SZ.
        """
        try:
            client = get_shared_client()
            from ..futu_client.types import MarketType
            mkt = MarketType(market) if market and market in ("HK", "US", "SH", "SZ") else None
            reminders = client.get_price_reminder(code=code, market=mkt)

            if not reminders:
                return "🔔 无到价提醒"

            lines = ["## 🔔 到价提醒列表\n"]
            lines.append("| 代码 | 类型 | 触发值 | 频率 | 启用 | 备注 |")
            lines.append("|------|------|--------|------|------|------|")

            for r in reminders:
                enabled = "✅" if r["enable"] else "❌"
                lines.append(
                    f"| {r['code']} | {r['reminder_type']} | {r['value']} | "
                    f"{r['reminder_freq']} | {enabled} | {r['note'] or '—'} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取到价提醒失败: {e}"

    @server.tool()
    async def futu_delete_price_reminder(code: str, key: int) -> str:
        """Delete a price reminder.

        Args:
            code: Stock code.
            key: Reminder key/ID (from futu_get_price_reminders).
        """
        try:
            client = get_shared_client()
            client.set_price_reminder(code, op="DELETE", key=key)
            return f"## 🗑️ 到价提醒已删除 (key: {key})"
        except Exception as e:
            return f"❌ 删除到价提醒失败: {e}"

    @server.tool()
    async def futu_start_monitor() -> str:
        """Start the background monitoring daemon for strategy-based alerts.

        Note: This is for advanced strategy monitoring. For simple price alerts, use futu_set_price_reminder.
        """
        # TODO: Implement daemon-based monitoring in Phase 3
        return """## 🔔 监控系统

**状态**: 开发中 (Phase 3)

当前可用功能:
- 使用 **futu_set_price_reminder** 设置原生到价提醒
- 到价提醒由 OpenD 网关直接处理，无需额外监控进程

策略驱动的自动监控将在后续版本中实现。"""

    @server.tool()
    async def futu_get_monitor_status() -> str:
        """Get current monitoring status and recent alerts."""
        try:
            client = get_shared_client()
            # Get all active reminders as current monitoring state
            reminders = client.get_price_reminder()
            active = [r for r in reminders if r.get("enable")]

            lines = ["## 📡 监控状态\n"]
            lines.append(f"**活跃提醒数**: {len(active)}")
            lines.append(f"**交易环境**: {get_config('futu_trd_env') or 'SIMULATE'}\n")

            if active:
                lines.append("### 活跃提醒")
                lines.append("| 代码 | 类型 | 触发值 | 备注 |")
                lines.append("|------|------|--------|------|")
                for r in active:
                    lines.append(f"| {r['code']} | {r['reminder_type']} | {r['value']} | {r['note'] or '—'} |")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取监控状态失败: {e}"
