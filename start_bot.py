#!/usr/bin/env python3
"""
Market Sim Bot Launcher
Simple script to start the Discord trading bot with proper error handling
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    load_dotenv()
    required_vars = ["TOKEN", "FINNHUB_API_KEY", "DISCORD_CHANNEL_ID"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4)}{value[-4:]}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Please update your .env file with the required values")
        return False
    
    return True

def main():
    print("🚀 Market Sim Discord Bot")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("\n🤖 Starting Discord bot...")
    print("💡 Press Ctrl+C to stop the bot")
    print("=" * 50)
    
    try:
        # Import and run the bot
        print("🤖 Loading bot modules...")
        import botsim_enhanced
        # The bot will start automatically when the module is imported
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        print("💡 Check your environment variables and internet connection")
        sys.exit(1)

if __name__ == "__main__":
    main()
