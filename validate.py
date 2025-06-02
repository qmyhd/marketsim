#!/usr/bin/env python3
"""
Pre-flight validation script for Market Sim
Checks if all dependencies and configuration are ready
"""

import os
import sys
from dotenv import load_dotenv

def check_files():
    """Check if all essential files exist"""
    print("📁 Checking essential files...")
    
    essential_files = [
        "botsim_enhanced.py",
        "dashboard_robinhood.py", 
        "start_bot.py",
        "start_dashboard.py",
        "requirements.txt",
        ".env"
    ]
    
    missing_files = []
    for file in essential_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")
    
    return len(missing_files) == 0

def check_environment():
    """Check environment variables"""
    print("\n🔍 Checking environment variables...")
    
    load_dotenv()
    required_vars = ["TOKEN", "FINNHUB_API_KEY", "DISCORD_CHANNEL_ID"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            masked_value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "*" * len(value)
            print(f"✅ {var}: {masked_value}")
    
    return len(missing_vars) == 0

def check_imports():
    """Check if key dependencies can be imported"""
    print("\n📦 Checking dependencies...")
    
    dependencies = [
        ("discord", "Discord.py"),
        ("aiosqlite", "aiosqlite"),
        ("aiohttp", "aiohttp"),
        ("matplotlib", "matplotlib"),
        ("flask", "Flask"),
        ("requests", "requests"),
        ("dotenv", "python-dotenv")
    ]
    
    failed_imports = []
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            failed_imports.append(name)
            print(f"❌ {name}")
    
    return len(failed_imports) == 0

def main():
    print("🚀 Market Sim Pre-flight Check")
    print("=" * 50)
    
    files_ok = check_files()
    env_ok = check_environment()
    imports_ok = check_imports()
    
    print("\n📊 Summary:")
    print("=" * 50)
    
    if files_ok and env_ok and imports_ok:
        print("🎉 All checks passed! You're ready to run Market Sim.")
        print("\n🚀 To start:")
        print("  Bot:       python start_bot.py")
        print("  Dashboard: python start_dashboard.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        
        if not files_ok:
            print("💡 Run this script from the Market_sim directory")
        
        if not env_ok:
            print("💡 Update your .env file with the required variables")
            
        if not imports_ok:
            print("💡 Install dependencies: pip install -r requirements.txt")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
