"""
Market Sim Database Operations Module
====================================

This module provides all database operations for the Market Sim trading bot.
It uses SQLite with aiosqlite for async operations and is optimized for minimal
memory usage on Fly.io free tier deployments.

Database Schema:
- users: Discord user accounts with cash balances and portfolio tracking
- holdings: Stock positions with shares and average cost basis
- history: Daily portfolio value snapshots for performance charts
- last_price: Cached stock prices with timestamps for API efficiency

Key Features:
- Async/await operations for non-blocking database access
- Automatic schema creation and migration
- Memory-optimized connection settings
- Type-safe operations with proper error handling
- Configurable starting capital via environment variables

Environment Variables:
- DATABASE_URL: Path to SQLite file (default: /data/trading_game.db)
- DEFAULT_STARTING_CASH: Starting capital for new users (default: 1,000,000)
"""

import os
import aiosqlite
from datetime import date
from typing import Optional, List, Tuple, Any

# Database configuration
DB_NAME = os.getenv("DATABASE_URL", "/data/trading_game.db")
DEFAULT_STARTING_CASH = int(os.getenv("DEFAULT_STARTING_CASH", "1000000"))

# Connection pool settings optimized for minimal memory usage
SQLITE_SETTINGS = {
    "isolation_level": None,  # Autocommit mode for better performance
    "check_same_thread": False,  # Allow multi-threaded access
}

async def init_db() -> None:
    """
    Initialize the database schema by creating all required tables.
    
    Creates four main tables:
    1. users: Discord user accounts with financial data
    2. holdings: Individual stock positions 
    3. history: Daily portfolio value snapshots
    4. last_price: Cached stock price data
    
    This function is idempotent - it can be called multiple times safely.
    Uses IF NOT EXISTS to avoid errors on existing databases.
    
    Raises:
        aiosqlite.Error: If database creation fails
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                cash REAL DEFAULT {DEFAULT_STARTING_CASH},
                initial_value REAL DEFAULT {DEFAULT_STARTING_CASH},
                last_value REAL DEFAULT {DEFAULT_STARTING_CASH},
                username TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                user_id TEXT,
                symbol TEXT,
                shares INTEGER,
                avg_price REAL,
                PRIMARY KEY (user_id, symbol)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                user_id TEXT,
                date TEXT,
                portfolio_value REAL,
                PRIMARY KEY (user_id, date)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS last_price (
                symbol TEXT PRIMARY KEY,
                price REAL,
                last_updated TEXT
            )
            """
        )
        await db.commit()

async def get_user(user_id: str) -> Optional[Tuple[Any, ...]] :
    """
    Retrieve complete user record from the database.
    
    Args:
        user_id: Discord user ID as string
        
    Returns:
        Complete user tuple (user_id, cash, initial_value, last_value, username)
        or None if user doesn't exist
        
    Example:
        user = await get_user("123456789")
        if user:
            user_id, cash, initial, last, username = user
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()


async def create_user(user_id: str, username: str) -> None:
    """
    Create a new user account with default starting capital.
    
    Args:
        user_id: Discord user ID as string
        username: Discord display name for the user
        
    Raises:
        aiosqlite.IntegrityError: If user already exists (PRIMARY KEY violation)
        
    Note:
        Sets cash and initial_value to DEFAULT_STARTING_CASH from environment
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, cash, username) VALUES (?, ?, ?)",
            (user_id, DEFAULT_STARTING_CASH, username),
        )
        await db.commit()


async def get_cash(user_id: str) -> Optional[float]:
    """
    Get the current cash balance for a user.
    
    Args:
        user_id: Discord user ID as string
        
    Returns:
        Current cash balance as float, or None if user doesn't exist
        
    Example:
        cash = await get_cash("123456789")
        if cash is not None:
            print(f"User has ${cash:,.2f} available")
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def update_cash(user_id: str, cash: float) -> None:
    """Update a user's cash balance."""
    if cash < 0:
        raise ValueError(f"Cash balance cannot be negative: {cash}")
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (cash, user_id))
        await db.commit()

async def get_holdings(user_id: str) -> list[tuple[str, int, float]]:
    """Return all holdings for a user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            # Ensure shares are integers and avg_price are floats
            return [(symbol, int(shares), float(avg_price)) for symbol, shares, avg_price in rows]

async def get_holding(user_id: str, symbol: str) -> tuple[int, float] | None:
    """Return a single holding for a user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        ) as cur:
            row = await cur.fetchone()
            return (int(row[0]), float(row[1])) if row else None

async def update_holding(user_id: str, symbol: str, shares: int, avg_price: float) -> None:
    """Modify share count and average price for a holding."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE holdings SET shares = ?, avg_price = ? WHERE user_id = ? AND symbol = ?",
            (shares, avg_price, user_id, symbol),
        )
        await db.commit()

async def insert_holding(user_id: str, symbol: str, shares: int, avg_price: float) -> None:
    """Add a new holding record."""
    if shares <= 0:
        raise ValueError(f"Shares must be positive: {shares}")
    if avg_price <= 0:
        raise ValueError(f"Average price must be positive: {avg_price}")
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO holdings (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)",
            (user_id, symbol, shares, avg_price),
        )
        await db.commit()

async def delete_holding(user_id: str, symbol: str) -> None:
    """Remove a holding from a user's portfolio."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM holdings WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        )
        await db.commit()

async def record_history(user_id: str, value: float) -> None:
    """Save a daily snapshot of a user's portfolio value."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO history (user_id, date, portfolio_value) VALUES (?, ?, ?)",
            (user_id, today, value),
        )
        await db.commit()

async def update_last_price(db: aiosqlite.Connection, symbol: str, price: float) -> None:
    """Persist latest price for a ticker."""
    await db.execute(
        "INSERT OR REPLACE INTO last_price (symbol, price, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (symbol.upper(), price),
    )

async def get_last_price_from_db(symbol: str) -> float | None:
    """Retrieve the last stored price for a ticker."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT price FROM last_price WHERE symbol = ?",
            (symbol.upper(),),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def get_all_users() -> list[tuple[str, float, float, float]]:
    """Return basic info for all users."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, cash, initial_value, last_value FROM users") as cur:
            return await cur.fetchall()

async def get_history(user_id: str) -> list[tuple[str, float]]:
    """Return the historical portfolio value for a user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT date, portfolio_value FROM history WHERE user_id = ? ORDER BY date",
            (user_id,),
        ) as cur:
            return await cur.fetchall()
