#!/usr/bin/env python3
"""
Market Sim Dashboard Launcher
Simple script to start the web dashboard with proper error handling
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    load_dotenv()
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    if not finnhub_key:
        print("❌ Missing FINNHUB_API_KEY environment variable")
        print("💡 Please update your .env file with your Finnhub API key")
        return False
    else:
        print(f"✅ FINNHUB_API_KEY: {'*' * (len(finnhub_key) - 4)}{finnhub_key[-4:]}")
    
    return True

def main():
    print("📊 Market Sim Web Dashboard")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("\n🌐 Starting web dashboard...")
    print("💡 Visit http://localhost:8080 to view the dashboard")
    print("💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Import and run the dashboard
        from dashboard_robinhood import app
        print("🚀 Starting Flask server...")
        app.run(debug=False, host="0.0.0.0", port=8080)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        print("💡 Check your environment variables and that port 8080 is available")
        sys.exit(1)

if __name__ == "__main__":
    main()
