"""Database helpers for Market Sim."""
import os
import aiosqlite
from datetime import date

DB_NAME = os.getenv("DATABASE_URL", "/data/trading_game.db")
DEFAULT_STARTING_CASH = int(os.getenv("DEFAULT_STARTING_CASH", "1000000"))

async def init_db() -> None:
    """Create database tables if they do not exist."""
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
                last_price REAL,
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

async def get_user(user_id: str) -> tuple | None:
    """Return user row or None if not found."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

async def create_user(user_id: str, username: str) -> None:
    """Insert a new user with starting cash."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, cash, username) VALUES (?, ?, ?)",
            (user_id, DEFAULT_STARTING_CASH, username),
        )
        await db.commit()

async def get_cash(user_id: str) -> float | None:
    """Return the user's cash balance."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def update_cash(user_id: str, cash: float) -> None:
    """Update a user's cash balance."""
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
            return await cur.fetchall()

async def get_holding(user_id: str, symbol: str) -> tuple[int, float] | None:
    """Return a single holding for a user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT shares, avg_price FROM holdings WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        ) as cur:
            return await cur.fetchone()

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
