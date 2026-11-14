import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any


INITIAL_HOLDINGS = {
    "NVDA": 1,
    "ORCL": 5,
    "PLTR": 1,
    "MRVL": 2,
    "FTNT": 1,
    "ABBV": 1,
    "MP": 1,
    "PG": 12,
}

_TICKER_PATTERN = re.compile(r"^[A-Z0-9.^=-]{1,16}$")


def _database_path() -> Path:
    configured = os.environ.get("NOVA_DATA_PATH")
    return Path(configured).expanduser() if configured else Path.home() / ".nova" / "nova.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)
    connection = sqlite3.connect(path, timeout=10)
    if os.name == "posix":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _database():
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_storage() -> None:
    with _database() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS holdings (
                ticker TEXT PRIMARY KEY,
                shares REAL NOT NULL CHECK (shares > 0),
                cost_basis REAL CHECK (cost_basis IS NULL OR cost_basis > 0),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS saved_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        seeded = connection.execute(
            "SELECT value FROM app_metadata WHERE key = 'initial_holdings_seeded'"
        ).fetchone()
        if not seeded:
            connection.executemany(
                "INSERT OR IGNORE INTO holdings (ticker, shares) VALUES (?, ?)",
                INITIAL_HOLDINGS.items(),
            )
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES ('initial_holdings_seeded', '1')"
            )


def normalize_ticker(ticker: str) -> str:
    normalized = str(ticker).strip().upper()
    if not _TICKER_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid ticker symbol.")
    return normalized


def get_holdings() -> dict[str, dict[str, float | None]]:
    with _database() as connection:
        rows = connection.execute(
            "SELECT ticker, shares, cost_basis FROM holdings ORDER BY ticker"
        ).fetchall()
    return {
        row["ticker"]: {
            "shares": float(row["shares"]),
            "cost_basis": (
                float(row["cost_basis"]) if row["cost_basis"] is not None else None
            ),
        }
        for row in rows
    }


def save_holding(ticker: str, shares: float, cost_basis: float | None = None) -> None:
    symbol = normalize_ticker(ticker)
    quantity = float(shares)
    cost = float(cost_basis) if cost_basis is not None else None
    if quantity <= 0:
        raise ValueError("Shares must be greater than zero.")
    if cost is not None and cost <= 0:
        raise ValueError("Cost basis per share must be greater than zero.")
    with _database() as connection:
        connection.execute(
            """INSERT INTO holdings (ticker, shares, cost_basis, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(ticker) DO UPDATE SET
               shares = excluded.shares,
               cost_basis = excluded.cost_basis,
               updated_at = CURRENT_TIMESTAMP""",
            (symbol, quantity, cost),
        )


def remove_holding(ticker: str) -> None:
    with _database() as connection:
        connection.execute(
            "DELETE FROM holdings WHERE ticker = ?", (normalize_ticker(ticker),)
        )


def get_watchlist() -> list[str]:
    with _database() as connection:
        rows = connection.execute(
            "SELECT ticker FROM watchlist ORDER BY added_at, ticker"
        ).fetchall()
    return [row["ticker"] for row in rows]


def add_to_watchlist(ticker: str) -> None:
    with _database() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)",
            (normalize_ticker(ticker),),
        )


def remove_from_watchlist(ticker: str) -> None:
    with _database() as connection:
        connection.execute(
            "DELETE FROM watchlist WHERE ticker = ?", (normalize_ticker(ticker),)
        )


def save_document(title: str, subject: str, content: str) -> int:
    clean_title = str(title).strip()
    clean_content = str(content).strip()
    if not clean_title or not clean_content:
        raise ValueError("A document title and content are required.")
    with _database() as connection:
        cursor = connection.execute(
            "INSERT INTO saved_documents (title, subject, content) VALUES (?, ?, ?)",
            (clean_title[:200], str(subject).strip()[:100], clean_content),
        )
        return int(cursor.lastrowid)


def get_saved_documents() -> list[dict[str, Any]]:
    with _database() as connection:
        rows = connection.execute(
            """SELECT id, title, subject, content, created_at
               FROM saved_documents ORDER BY id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def get_app_setting(key: str, default: str = "") -> str:
    with _database() as connection:
        row = connection.execute(
            "SELECT value FROM app_settings WHERE key = ?", (str(key),)
        ).fetchone()
    return str(row["value"]) if row else default


def set_app_setting(key: str, value: str) -> None:
    with _database() as connection:
        connection.execute(
            """INSERT INTO app_settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (str(key), str(value)),
        )
