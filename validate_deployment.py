#!/usr/bin/env python3
"""
Pre-deployment validation script for Market Sim
Ensures everything is ready for cost-optimized Fly.io deployment
"""

import asyncio
import os
import sqlite3
import sys
from pathlib import Path

async def validate_database():
    """Validate database structure and sample data."""
    print("🗄️  Validating Database...")
    
    try:
        conn = sqlite3.connect('trading_game.db')
        
        # Check tables exist
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        expected_tables = {'users', 'holdings', 'history', 'last_price'}
        found_tables = {table[0] for table in tables}
        
        if not expected_tables.issubset(found_tables):
            missing = expected_tables - found_tables
            print(f"❌ Missing tables: {missing}")
            return False
        
        # Check sample data
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        holdings_count = conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
        
        print(f"   ✅ All tables present: {sorted(found_tables)}")
        print(f"   ✅ Users: {user_count}")
        print(f"   ✅ Holdings: {holdings_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False

def validate_environment():
    """Check critical environment variables."""
    print("🔧 Validating Environment Variables...")
    
    required_vars = {
        'TOKEN': 'Discord bot token',
        'FINNHUB_API_KEY': 'Primary Finnhub API key',
        'DISCORD_CHANNEL_ID': 'Discord channel ID',
        'DISCORD_WEBHOOK_URL': 'Discord webhook URL'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
        else:
            print(f"   ✅ {var}: Set")
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"     - {var}")
        return False
    
    # Check optional backup keys
    backup_keys = ['FINNHUB_API_KEY_SECOND', 'FINNHUB_API_KEY_2']
    backup_count = sum(1 for key in backup_keys if os.getenv(key))
    print(f"   ✅ Backup API keys: {backup_count}/2 configured")
    
    return True

def validate_files():
    """Check all required files are present."""
    print("📁 Validating Required Files...")
    
    required_files = [
        'bot.py', 'database.py', 'prices.py', 'webhook_bot.py',
        'dashboard_robinhood.py', 'requirements.txt',
        'Dockerfile', 'Dockerfile.bot', 'fly.toml', 'fly.bot.toml',
        'commands/trading.py', 'commands/stats.py', 'commands/admin.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"   ✅ {file_path}")
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"     - {file_path}")
        return False
    
    return True

def validate_cost_optimization():
    """Check Fly.io configuration is optimized for free tier."""
    print("💰 Validating Cost Optimization...")
    
    # Check fly.toml settings
    try:
        with open('fly.toml', 'r') as f:
            fly_config = f.read()
            
        checks = [
            ('min_machines_running = 0', 'Apps start at 0 machines'),
            ('memory_mb = 256', 'Minimal memory allocation'),
            ('cpu_kind = "shared"', 'Shared CPU for lowest cost'),
            ('auto_stop_machines = "stop"', 'Auto-stop enabled'),
        ]
        
        for check, description in checks:
            if check in fly_config:
                print(f"   ✅ {description}")
            else:
                print(f"   ⚠️  {description} - not found in fly.toml")
        
        return True
        
    except Exception as e:
        print(f"❌ Could not validate fly.toml: {e}")
        return False

async def main():
    """Run all validation checks."""
    print("🔍 Market Sim Pre-Deployment Validation")
    print("=" * 50)
    
    checks = [
        ("Files", validate_files()),
        ("Environment", validate_environment()),
        ("Database", await validate_database()),
        ("Cost Optimization", validate_cost_optimization()),
    ]
    
    print("\n📊 Validation Summary:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ready for deployment.")
        print("\n📝 Next steps:")
        print("1. Deploy with: flyctl launch")
        print("2. Set secrets with: flyctl secrets set")
        print("3. Use: python fly_manager.py start/stop")
        print("4. Remember to scale to 0 when not in use!")
        sys.exit(0)
    else:
        print("❌ VALIDATION FAILED. Fix issues before deployment.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
