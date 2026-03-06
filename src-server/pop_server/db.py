"""SQLite database for users and usage tracking."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pop_server.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE NOT NULL,
    discord_username TEXT NOT NULL DEFAULT '',
    discord_avatar TEXT NOT NULL DEFAULT '',
    stripe_customer_id TEXT NOT NULL DEFAULT '',
    subscription_status TEXT NOT NULL DEFAULT 'none',
    subscription_id TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    last_login REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    endpoint TEXT NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage_log(user_id, created_at);
"""


def get_db() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_user(
    discord_id: str,
    discord_username: str,
    discord_avatar: str,
) -> dict:
    """Insert or update a user by Discord ID. Returns the user row as a dict."""
    now = time.time()
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO users (discord_id, discord_username, discord_avatar, created_at, last_login)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(discord_id) DO UPDATE SET
                   discord_username = excluded.discord_username,
                   discord_avatar = excluded.discord_avatar,
                   last_login = excluded.last_login""",
            (discord_id, discord_username, discord_avatar, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by internal ID."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_discord_id(discord_id: str) -> dict | None:
    """Fetch a user by Discord ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_subscription(
    discord_id: str,
    stripe_customer_id: str,
    subscription_id: str,
    subscription_status: str,
) -> None:
    """Update a user's subscription info."""
    conn = get_db()
    try:
        conn.execute(
            """UPDATE users SET
                stripe_customer_id = ?,
                subscription_id = ?,
                subscription_status = ?
               WHERE discord_id = ?""",
            (stripe_customer_id, subscription_id, subscription_status, discord_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_subscription_by_customer(
    stripe_customer_id: str,
    subscription_id: str,
    subscription_status: str,
) -> None:
    """Update subscription info by Stripe customer ID."""
    conn = get_db()
    try:
        conn.execute(
            """UPDATE users SET
                subscription_id = ?,
                subscription_status = ?
               WHERE stripe_customer_id = ?""",
            (subscription_id, subscription_status, stripe_customer_id),
        )
        conn.commit()
    finally:
        conn.close()


def log_usage(user_id: int, endpoint: str, tokens_used: int = 0) -> None:
    """Record an AI API call in the usage log."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO usage_log (user_id, endpoint, tokens_used, created_at) VALUES (?, ?, ?, ?)",
            (user_id, endpoint, tokens_used, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_daily_usage_count(user_id: int) -> int:
    """Count AI requests for a user in the last 24 hours."""
    cutoff = time.time() - 86400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_log WHERE user_id = ? AND created_at > ?",
            (user_id, cutoff),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()
