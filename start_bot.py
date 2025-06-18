#!/usr/bin/env python3
"""
Market Sim Bot Launcher
Simple script to start the Discord trading bot with proper error handling
"""

import os
import sys
from dotenv import load_dotenv

def check_environment() -> bool:
    """Check if all required environment variables are set."""
    print("🔍 Checking environment variables...")
    load_dotenv()
    required_vars = ["FINNHUB_API_KEY", "TOKEN"]  # TOKEN is required for Discord bot
    optional_vars = ["DISCORD_WEBHOOK_URL", "BOT_COMMAND"]
    missing = []

    for var in required_vars + optional_vars:
        value = os.getenv(var)
        if not value:
            if var in required_vars:
                missing.append(var)
            else:
                print(f"⚠️ {var}: Not set (optional)")
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4)}{value[-4:]}")

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("💡 Please update your .env file with the required values")
        return False
    
    return True

def main() -> None:
    """Run the helper script to launch the Discord bot."""
    print("🚀 Market Sim Discord Bot")
    print("=" * 50)
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("\n🤖 Starting Discord bot...")
    print("=" * 50)

    try:
        from bot import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error running bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
