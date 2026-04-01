"""Strategy management tools — templates, CRUD."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server

from ..storage.db import get_db


STRATEGY_TEMPLATES = {
    "sma_crossover": {
        "name": "SMA 均线交叉",
        "description": "当短期均线上穿长期均线时买入，下穿时卖出。经典趋势跟踪策略。",
        "universe": [],
        "rules": [
            {
                "trigger": "cron",
                "schedule": "0 9 31 * * 1-5",
                "conditions": [
                    {"indicator": "sma", "params": {"period": 10}, "op": "cross_above", "target": "sma", "target_params": {"period": 30}}
                ],
                "actions": [
                    {"type": "buy", "sizing": "percent_of_equity", "value": 10}
                ],
            },
            {
                "trigger": "cron",
                "schedule": "0 9 31 * * 1-5",
                "conditions": [
                    {"indicator": "sma", "params": {"period": 10}, "op": "cross_below", "target": "sma", "target_params": {"period": 30}}
                ],
                "actions": [
                    {"type": "sell", "sizing": "all"}
                ],
            },
        ],
        "risk_management": {"max_position_pct": 20, "stop_loss_pct": 5, "take_profit_pct": 15},
    },
    "dca": {
        "name": "定投 (DCA)",
        "description": "定期定额买入，降低择时风险。适合长期投资者。",
        "universe": [],
        "rules": [
            {
                "trigger": "cron",
                "schedule": "0 10 0 * * 1",
                "conditions": [],
                "actions": [
                    {"type": "buy", "sizing": "fixed_amount", "value": 5000}
                ],
            },
        ],
        "risk_management": {"max_position_pct": 30, "stop_loss_pct": 15},
    },
    "mean_reversion": {
        "name": "均值回归",
        "description": "股价偏离均线过多时反向操作。适合震荡市场。",
        "universe": [],
        "rules": [
            {
                "trigger": "cron",
                "schedule": "0 10 0 * * 1-5",
                "conditions": [
                    {"indicator": "price_vs_sma", "params": {"period": 20}, "op": "lt", "value": -3}
                ],
                "actions": [
                    {"type": "buy", "sizing": "percent_of_equity", "value": 5}
                ],
            },
            {
                "trigger": "cron",
                "schedule": "0 10 0 * * 1-5",
                "conditions": [
                    {"indicator": "price_vs_sma", "params": {"period": 20}, "op": "gt", "value": 3}
                ],
                "actions": [
                    {"type": "sell", "sizing": "all"}
                ],
            },
        ],
        "risk_management": {"max_position_pct": 15, "stop_loss_pct": 8, "take_profit_pct": 10},
    },
    "momentum": {
        "name": "动量策略",
        "description": "买入近期表现最强的股票，卖出最弱的。适合趋势明确的市场。",
        "universe": [],
        "rules": [
            {
                "trigger": "cron",
                "schedule": "0 10 0 * * 1",
                "conditions": [
                    {"indicator": "change_rate", "params": {"period": 20}, "op": "gt", "value": 5}
                ],
                "actions": [
                    {"type": "buy", "sizing": "percent_of_equity", "value": 10}
                ],
            },
        ],
        "risk_management": {"max_position_pct": 20, "stop_loss_pct": 7, "take_profit_pct": 20},
    },
    "trailing_stop": {
        "name": "追踪止损",
        "description": "买入后设置追踪止损，锁定利润的同时限制亏损。",
        "universe": [],
        "rules": [
            {
                "trigger": "alert",
                "conditions": [
                    {"indicator": "trailing_drawdown_pct", "op": "gt", "value": 5}
                ],
                "actions": [
                    {"type": "sell", "sizing": "all"},
                    {"type": "notify", "message": "追踪止损触发: $symbol 从高点回撤超过5%"},
                ],
            },
        ],
        "risk_management": {"trailing_stop_pct": 5},
    },
}


def register_strategy_tools(server: Server) -> None:
    @server.tool()
    async def futu_list_strategy_templates() -> str:
        """List all built-in strategy templates."""
        lines = ["## 📋 策略模板\n"]
        for key, tmpl in STRATEGY_TEMPLATES.items():
            rm = tmpl.get("risk_management", {})
            sl = rm.get("stop_loss_pct", "N/A")
            tp = rm.get("take_profit_pct", "N/A")
            lines.append(f"### {tmpl['name']} (`{key}`)")
            lines.append(f"{tmpl['description']}")
            lines.append(f"- 止损: {sl}% | 止盈: {tp}%")
            lines.append("")
        lines.append("使用 `futu_create_strategy` 从模板创建，或自定义规则。")
        return "\n".join(lines)

    @server.tool()
    async def futu_create_strategy(
        name: str,
        description: str = "",
        template: str | None = None,
        universe: str = "",
        rules: str = "",
        risk_management: str = "",
    ) -> str:
        """Create a trading strategy from a template or custom rules.

        Args:
            name: Strategy name.
            description: Strategy description.
            template: Template key (sma_crossover, dca, mean_reversion, momentum, trailing_stop).
            universe: Comma-separated stock codes, e.g. "HK.00700,US.AAPL".
            rules: JSON string of custom rules (overrides template rules).
            risk_management: JSON string of risk management params.
        """
        strategy_id = str(uuid.uuid4())[:8]

        if template and template in STRATEGY_TEMPLATES:
            tmpl = STRATEGY_TEMPLATES[template]
            strategy_rules = json.dumps(tmpl["rules"])
            strategy_rm = json.dumps(tmpl.get("risk_management", {}))
            description = description or tmpl["description"]
        else:
            strategy_rules = rules or "[]"
            strategy_rm = risk_management or "{}"

        universe_list = json.dumps([c.strip() for c in universe.split(",") if c.strip()])

        db = get_db()
        db.execute(
            "INSERT INTO strategies (id, name, description, universe, rules, risk_management) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (strategy_id, name, description, universe_list, strategy_rules, strategy_rm),
        )
        db.commit()

        return f"""## ✅ 策略已创建

**ID**: {strategy_id}
**名称**: {name}
**描述**: {description}
**标的**: {universe or '待设置'}
**模板**: {template or '自定义'}

接下来建议：用 **futu_backtest** 回测验证策略效果。"""

    @server.tool()
    async def futu_list_strategies() -> str:
        """List all saved strategies."""
        db = get_db()
        rows = db.execute(
            "SELECT id, name, description, universe, is_active, created_at FROM strategies ORDER BY created_at DESC"
        ).fetchall()

        if not rows:
            return "📋 尚无保存的策略。使用 **futu_create_strategy** 创建。"

        lines = ["## 📋 策略列表\n"]
        lines.append("| ID | 名称 | 描述 | 标的 | 状态 | 创建时间 |")
        lines.append("|----|------|------|------|------|----------|")

        for r in rows:
            status = "🟢 活跃" if r["is_active"] else "⬜ 未激活"
            universe = json.loads(r["universe"]) if r["universe"] else []
            u_str = ", ".join(universe[:3]) + ("..." if len(universe) > 3 else "") if universe else "—"
            lines.append(
                f"| {r['id']} | {r['name']} | {r['description'] or '—'} | {u_str} | {status} | {r['created_at']} |"
            )

        return "\n".join(lines)

    @server.tool()
    async def futu_get_strategy(strategy_id: str) -> str:
        """Get detailed strategy information.

        Args:
            strategy_id: Strategy ID.
        """
        db = get_db()
        row = db.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()

        if not row:
            return f"❌ 策略 {strategy_id} 不存在"

        rules = json.loads(row["rules"]) if row["rules"] else []
        rm = json.loads(row["risk_management"]) if row["risk_management"] else {}
        universe = json.loads(row["universe"]) if row["universe"] else []

        return f"""## 📋 策略详情

**ID**: {row['id']}
**名称**: {row['name']}
**描述**: {row['description'] or '—'}
**标的**: {', '.join(universe) or '—'}
**状态**: {'🟢 活跃' if row['is_active'] else '⬜ 未激活'}
**创建时间**: {row['created_at']}
**更新时间**: {row['updated_at']}

### 规则
```json
{json.dumps(rules, indent=2, ensure_ascii=False)}
```

### 风险管理
```json
{json.dumps(rm, indent=2, ensure_ascii=False)}
```"""

    @server.tool()
    async def futu_delete_strategy(strategy_id: str) -> str:
        """Delete a strategy.

        Args:
            strategy_id: Strategy ID.
        """
        db = get_db()
        db.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
        db.commit()
        return f"## 🗑️ 策略 {strategy_id} 已删除"
