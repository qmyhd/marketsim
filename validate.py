#!/usr/bin/env python3
"""
Pre-flight validation script for Market Sim
Checks if all dependencies and configuration are ready
"""

import os
import sys
import asyncio
import pkgutil
from importlib import import_module
from dotenv import load_dotenv
from discord.ext import commands
import discord

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
    required_vars = ["FINNHUB_API_KEY"]
    optional_vars = ["DISCORD_WEBHOOK_URL", "BOT_COMMAND"]

    missing_required = []

    for var in required_vars + optional_vars:
        value = os.getenv(var)
        if not value:
            if var in required_vars:
                missing_required.append(var)
                print(f"❌ {var}: Not set")
            else:
                print(f"⚠️ {var}: Not set (optional)")
        else:
            masked_value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "*" * len(value)
            print(f"✅ {var}: {masked_value}")

    return len(missing_required) == 0

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

def check_commands_imports() -> bool:
    """Ensure all command modules can be imported."""
    print("\n📚 Checking command modules...")
    success = True
    for finder, name, _ in pkgutil.iter_modules(["commands"]):
        if name.startswith("_"):
            continue
        module_name = f"commands.{name}"
        try:
            import_module(module_name)
            print(f"✅ {module_name}")
        except Exception as exc:
            success = False
            print(f"❌ {module_name}: {exc}")
    return success

async def check_cog_setup() -> bool:
    """Load each cog and call its setup(bot)."""
    print("\n🧩 Checking cog setup...")
    intents = discord.Intents.none()
    bot = commands.Bot(command_prefix="!", intents=intents)
    success = True
    for finder, name, _ in pkgutil.iter_modules(["commands"]):
        if name.startswith("_"):
            continue
        module = import_module(f"commands.{name}")
        setup = getattr(module, "setup", None)
        if not setup:
            print(f"❌ {module.__name__} lacks setup()")
            success = False
            continue
        try:
            if asyncio.iscoroutinefunction(setup):
                await setup(bot)
            else:
                setup(bot)
            print(f"✅ {module.__name__}.setup")
        except Exception as exc:
            print(f"❌ {module.__name__}.setup: {exc}")
            success = False
    return success

def main():
    print("🚀 Market Sim Pre-flight Check")
    print("=" * 50)
    
    files_ok = check_files()
    env_ok = check_environment()
    imports_ok = check_imports()
    commands_ok = check_commands_imports()
    try:
        cogs_ok = asyncio.run(check_cog_setup())
    except Exception as exc:
        print(f"❌ Cog setup failed: {exc}")
        cogs_ok = False
    
    print("\n📊 Summary:")
    print("=" * 50)
    
    if files_ok and env_ok and imports_ok and commands_ok and cogs_ok:
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
        if not commands_ok:
            print("💡 Fix import errors in commands modules")
        if not cogs_ok:
            print("💡 Ensure each cog has a working setup(bot) function")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
