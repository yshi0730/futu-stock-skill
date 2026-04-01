"""SQLite storage layer — config, strategies, trades, alerts, backtests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_db: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _db
    if _db is not None:
        return _db

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DATA_DIR / "futu-skill.db"
    _db = sqlite3.connect(str(db_path))
    _db.row_factory = sqlite3.Row
    _db.execute("PRAGMA journal_mode=WAL")
    _db.execute("PRAGMA foreign_keys=ON")
    _migrate(_db)
    return _db


def _migrate(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS strategies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            universe TEXT NOT NULL DEFAULT '[]',
            rules TEXT NOT NULL,
            risk_management TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL,
            total REAL,
            strategy_id TEXT,
            status TEXT NOT NULL,
            filled_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS alert_rules (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_triggered_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS alert_history (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            acknowledged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS position_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot TEXT NOT NULL,
            total_equity REAL NOT NULL,
            total_pnl REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS backtests (
            id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            config TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
        CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at);
        CREATE INDEX IF NOT EXISTS idx_alert_history_created ON alert_history(created_at);
        CREATE INDEX IF NOT EXISTS idx_position_snapshots_created ON position_snapshots(created_at);
    """)
    db.commit()


def get_config(key: str) -> str | None:
    db = get_db()
    row = db.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(key: str, value: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO config (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value),
    )
    db.commit()
