#!/usr/bin/env python3
"""
Update starting capital for existing users from $100k to $1M
This script adds $900k to users who started with the old $100k capital
"""

import sqlite3
import os
from datetime import date

DB_NAME = os.getenv("DATABASE_URL", "/data/trading_game.db")

def update_starting_capital():
    print("🔧 Updating starting capital for existing users...")
    
    if not os.path.exists(DB_NAME):
        print("❌ Database not found. Run the bot first to create it.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Current user table columns: {columns}")
        
        # Check for users with old $100k initial value
        cursor.execute("SELECT user_id, cash, initial_value, username FROM users WHERE initial_value = 100000")
        old_users = cursor.fetchall()
        
        if not old_users:
            print("✅ No users found with old $100k starting capital")
            return
            
        print(f"👥 Found {len(old_users)} users with old $100k capital:")
        
        for user_id, cash, initial_value, username in old_users:
            print(f"   - {username} (ID: {user_id}): Cash=${cash:,.2f}, Initial=${initial_value:,.2f}")
        
        # Ask for confirmation
        response = input("\n🤔 Update these users to $1M starting capital? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Update cancelled")
            return
            
        # Update users
        updated_count = 0
        for user_id, cash, initial_value, username in old_users:
            # Add $900k to both cash and initial_value
            new_cash = cash + 900000
            new_initial = 1000000
            
            cursor.execute(
                "UPDATE users SET cash = ?, initial_value = ? WHERE user_id = ?",
                (new_cash, new_initial, user_id)
            )
            
            print(f"✅ Updated {username}: Cash ${cash:,.2f} → ${new_cash:,.2f}, Initial ${initial_value:,.2f} → ${new_initial:,.2f}")
            updated_count += 1
        
        conn.commit()
        print(f"\n🎉 Successfully updated {updated_count} users!")
        print("💡 All users now have $1M starting capital")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_starting_capital()
