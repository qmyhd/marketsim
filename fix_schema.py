#!/usr/bin/env python3
"""
Fix the database schema to have correct default values of 1,000,000
"""

import sqlite3
import os
import shutil

DB_NAME = os.getenv("DATABASE_URL", "/data/trading_game.db")

def fix_schema():
    print("🔧 Fixing database schema defaults...")
    
    # Backup the database first
    backup_name = "trading_game_backup.db"
    if os.path.exists(backup_name):
        os.remove(backup_name)
    
    # Copy database for backup
    import shutil
    shutil.copy2(DB_NAME, backup_name)
    print(f"📦 Created backup: {backup_name}")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get current data
        cursor.execute("SELECT user_id, cash, initial_value, last_value, username FROM users")
        users_data = cursor.fetchall()
        
        cursor.execute("SELECT user_id, symbol, shares, avg_price FROM holdings")
        holdings_data = cursor.fetchall()
        
        cursor.execute("SELECT user_id, date, portfolio_value FROM history")
        history_data = cursor.fetchall()
        
        print(f"📊 Found {len(users_data)} users, {len(holdings_data)} holdings, {len(history_data)} history records")
        
        # Drop and recreate tables with correct defaults
        cursor.execute("DROP TABLE IF EXISTS users_temp")
        cursor.execute("DROP TABLE IF EXISTS holdings_temp") 
        cursor.execute("DROP TABLE IF EXISTS history_temp")
        
        # Create new tables with correct defaults
        cursor.execute('''
            CREATE TABLE users_temp (
                user_id TEXT PRIMARY KEY,
                cash REAL DEFAULT 1000000,
                initial_value REAL DEFAULT 1000000,
                last_value REAL DEFAULT 1000000,
                username TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE holdings_temp (
                user_id TEXT,
                symbol TEXT,
                shares INTEGER,
                avg_price REAL,
                PRIMARY KEY (user_id, symbol)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE history_temp (
                user_id TEXT,
                date TEXT,
                portfolio_value REAL,
                PRIMARY KEY (user_id, date)
            )
        ''')
        
        # Insert data back
        cursor.executemany(
            "INSERT INTO users_temp (user_id, cash, initial_value, last_value, username) VALUES (?, ?, ?, ?, ?)",
            users_data
        )
        
        cursor.executemany(
            "INSERT INTO holdings_temp (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)",
            holdings_data
        )
        
        cursor.executemany(
            "INSERT INTO history_temp (user_id, date, portfolio_value) VALUES (?, ?, ?)",
            history_data
        )
        
        # Drop old tables and rename new ones
        cursor.execute("DROP TABLE users")
        cursor.execute("DROP TABLE holdings")
        cursor.execute("DROP TABLE history")
        
        cursor.execute("ALTER TABLE users_temp RENAME TO users")
        cursor.execute("ALTER TABLE holdings_temp RENAME TO holdings")
        cursor.execute("ALTER TABLE history_temp RENAME TO history")
        
        conn.commit()
        print("✅ Schema updated successfully!")
        
        # Verify the new schema
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("📋 New schema:")
        for col in columns:
            if col[1] in ['cash', 'initial_value', 'last_value']:
                print(f"   {col[1]}: default = {col[4]}")
        
        # Verify data integrity
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM holdings")
        holdings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM history")
        history_count = cursor.fetchone()[0]
        
        print(f"✅ Data verification: {user_count} users, {holdings_count} holdings, {history_count} history records")
        
        if user_count == len(users_data) and holdings_count == len(holdings_data) and history_count == len(history_data):
            print("🎉 All data preserved successfully!")
        else:
            print("⚠️ Data count mismatch - please check!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔄 Restoring from backup...")
        conn.close()
        os.remove(DB_NAME)
        shutil.copy2(backup_name, DB_NAME)
        print("📦 Backup restored")
        return False
    
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    success = fix_schema()
    if success:
        print("\n🚀 Schema fix completed successfully!")
    else:
        print("\n💥 Schema fix failed!")
