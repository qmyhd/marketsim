#!/usr/bin/env python3
"""
Database schema migration script for Market Sim.
Fixes the missing last_price column in holdings table.
"""

import asyncio
import sqlite3
import aiosqlite
from database import DB_NAME

async def check_schema() -> dict[str, list[str]]:
    """Check current database schema and return table structures."""
    schema_info = {}
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Get all tables
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cur:
            tables = await cur.fetchall()
        
        for (table_name,) in tables:
            async with db.execute(f"PRAGMA table_info({table_name})") as cur:
                columns = await cur.fetchall()
                schema_info[table_name] = [col[1] for col in columns]  # Column names
    
    return schema_info

async def fix_holdings_schema() -> None:
    """Add missing last_price column to holdings table if it doesn't exist."""
    schema = await check_schema()
    holdings_columns = schema.get("holdings", [])
    
    if "last_price" not in holdings_columns:
        print("⚠️  Missing 'last_price' column in holdings table. Adding it...")
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("ALTER TABLE holdings ADD COLUMN last_price REAL")
            await db.commit()
            print("✅ Added 'last_price' column to holdings table")
    else:
        print("✅ Holdings table schema is correct")

async def validate_data_integrity() -> None:
    """Validate data types and consistency."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Check for any invalid data types in shares column
        async with db.execute("SELECT user_id, symbol, shares FROM holdings WHERE CAST(shares AS INTEGER) != shares") as cur:
            invalid_shares = await cur.fetchall()
        
        if invalid_shares:
            print(f"⚠️  Found {len(invalid_shares)} holdings with non-integer shares:")
            for user_id, symbol, shares in invalid_shares:
                print(f"   User {user_id}: {symbol} has {shares} shares")
                # Fix by rounding to nearest integer
                await db.execute(
                    "UPDATE holdings SET shares = ROUND(shares) WHERE user_id = ? AND symbol = ?", 
                    (user_id, symbol)
                )
            await db.commit()
            print("✅ Fixed non-integer share values")
        else:
            print("✅ All shares data is valid")

async def main() -> None:
    """Main migration function."""
    print("🔧 Database Schema Migration Tool")
    print("=" * 40)
    
    # Check current schema
    print("\n📋 Current Database Schema:")
    schema = await check_schema()
    for table, columns in schema.items():
        print(f"  {table}: {', '.join(columns)}")
    
    # Fix schema issues
    print("\n🔧 Applying Schema Fixes:")
    await fix_holdings_schema()
    
    # Validate data integrity
    print("\n🔍 Validating Data Integrity:")
    await validate_data_integrity()
    
    print("\n✅ Database migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
