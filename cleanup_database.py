#!/usr/bin/env python3
"""
Database cleanup script for Market Sim.
Removes test/demo users and ensures data consistency.
"""

import asyncio
import sqlite3
import aiosqlite
from database import DB_NAME

# Known test/demo user patterns to remove
TEST_USER_PATTERNS = [
    'test_user_12345',
    'TestUser', 
    'Test Trader',
    'Demo User',
    'demo_user'
]

# Specific test user IDs to remove
SPECIFIC_TEST_USERS = [
    'test_user_12345'
]

# Known real Discord user IDs to keep
REAL_USERS = [
    '419660638881579028',  # Qais
    '236917392918183937',  # Jack  
    '1364782232761405470'  # Peter
]

async def check_database_contents() -> dict:
    """Check current database contents."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Get all users
        async with db.execute("SELECT user_id, username, cash, initial_value FROM users") as cur:
            users = await cur.fetchall()
        
        # Get all holdings
        async with db.execute("SELECT user_id, symbol, shares FROM holdings") as cur:
            holdings = await cur.fetchall()
            
        # Get all history
        async with db.execute("SELECT user_id, date, portfolio_value FROM history") as cur:
            history = await cur.fetchall()
    
    return {
        'users': users,
        'holdings': holdings, 
        'history': history
    }

def identify_test_users(users: list) -> list:
    """Identify test/demo users that should be removed."""
    test_users = []
    
    for user_id, username, cash, initial_value in users:
        # Check if it's a known real user
        if user_id in REAL_USERS:
            continue
            
        # Check specific test user IDs first
        if user_id in SPECIFIC_TEST_USERS:
            test_users.append(user_id)
            continue
            
        # Check if username matches test patterns (exact match)
        if username and username in TEST_USER_PATTERNS:
            test_users.append(user_id)
            continue
    
    return test_users

async def remove_test_users(test_user_ids: list) -> None:
    """Remove test users and all their associated data."""
    if not test_user_ids:
        print("✅ No test users found to remove")
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        for user_id in test_user_ids:
            print(f"🗑️  Removing test user: {user_id}")
            
            # Remove from holdings
            await db.execute("DELETE FROM holdings WHERE user_id = ?", (user_id,))
            
            # Remove from history
            await db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
            
            # Remove from users
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        await db.commit()
        print(f"✅ Removed {len(test_user_ids)} test users")

async def verify_user_consistency() -> None:
    """Verify user_id consistency across all tables."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Get all user_ids from users table
        async with db.execute("SELECT user_id FROM users") as cur:
            user_ids = {row[0] for row in await cur.fetchall()}
        
        # Check holdings table
        async with db.execute("SELECT DISTINCT user_id FROM holdings") as cur:
            holdings_user_ids = {row[0] for row in await cur.fetchall()}
            
        # Check history table
        async with db.execute("SELECT DISTINCT user_id FROM history") as cur:
            history_user_ids = {row[0] for row in await cur.fetchall()}
    
    print(f"📊 Users table: {len(user_ids)} users")
    print(f"📊 Holdings table: {len(holdings_user_ids)} unique users")
    print(f"📊 History table: {len(history_user_ids)} unique users")
    
    # Check for orphaned records
    orphaned_holdings = holdings_user_ids - user_ids
    orphaned_history = history_user_ids - user_ids
    
    if orphaned_holdings:
        print(f"⚠️  Found orphaned holdings for users: {orphaned_holdings}")
    if orphaned_history:
        print(f"⚠️  Found orphaned history for users: {orphaned_history}")
        
    if not orphaned_holdings and not orphaned_history:
        print("✅ All user_id references are consistent")

async def cleanup_orphaned_records() -> None:
    """Remove any orphaned records from holdings and history tables."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Get valid user_ids
        async with db.execute("SELECT user_id FROM users") as cur:
            valid_user_ids = {row[0] for row in await cur.fetchall()}
        
        # Remove orphaned holdings
        async with db.execute("SELECT DISTINCT user_id FROM holdings") as cur:
            holdings_user_ids = {row[0] for row in await cur.fetchall()}
        
        orphaned_holdings = holdings_user_ids - valid_user_ids
        if orphaned_holdings:
            for user_id in orphaned_holdings:
                await db.execute("DELETE FROM holdings WHERE user_id = ?", (user_id,))
            print(f"🗑️  Removed orphaned holdings for {len(orphaned_holdings)} users")
        
        # Remove orphaned history  
        async with db.execute("SELECT DISTINCT user_id FROM history") as cur:
            history_user_ids = {row[0] for row in await cur.fetchall()}
            
        orphaned_history = history_user_ids - valid_user_ids
        if orphaned_history:
            for user_id in orphaned_history:
                await db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
            print(f"🗑️  Removed orphaned history for {len(orphaned_history)} users")
        
        await db.commit()

async def main() -> None:
    """Main cleanup function."""
    print("🧹 Database Cleanup Tool")
    print("=" * 40)
    
    # Check current contents
    print("\n📋 Current Database Contents:")
    data = await check_database_contents()
    
    print(f"Users: {len(data['users'])}")
    for user_id, username, cash, initial_value in data['users']:
        print(f"  - {user_id}: {username} (Cash: ${cash:,.0f})")
    
    # Identify test users
    test_users = identify_test_users(data['users'])
    if test_users:
        print(f"\n🎯 Found {len(test_users)} test users to remove:")
        for user_id in test_users:
            user_data = next((u for u in data['users'] if u[0] == user_id), None)
            if user_data:
                print(f"  - {user_id}: {user_data[1]}")
        
        # Remove test users
        print(f"\n🗑️  Removing test users...")
        await remove_test_users(test_users)
    else:
        print("\n✅ No test users found")
    
    # Verify consistency
    print(f"\n🔍 Verifying User ID Consistency:")
    await verify_user_consistency()
    
    # Cleanup orphaned records
    print(f"\n🧹 Cleaning up orphaned records:")
    await cleanup_orphaned_records()
    
    # Final verification
    print(f"\n✅ Final Database State:")
    final_data = await check_database_contents()
    print(f"Users: {len(final_data['users'])}")
    print(f"Holdings: {len(final_data['holdings'])} records")
    print(f"History: {len(final_data['history'])} records")
    
    print(f"\n🎉 Database cleanup completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
