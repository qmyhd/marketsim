#!/usr/bin/env python3
"""
Fly.io Cost Management Helper for Market Sim
Automates starting/stopping apps to minimize hosting costs while staying on free tier.
"""

import subprocess
import sys
import time
from typing import List, Dict

class FlyManager:
    """Helper class for managing Fly.io apps cost-effectively."""
    
    def __init__(self):
        self.web_app = "market-sim-web"
        self.bot_app = "market-sim-bot"
    
    def run_command(self, command: List[str]) -> str:
        """Run a flyctl command and return output."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(command)}")
            print(f"Error: {e.stderr}")
            return ""
    
    def get_app_status(self, app_name: str) -> Dict[str, str]:
        """Get the current status of an app."""
        output = self.run_command(["flyctl", "-a", app_name, "status"])
        lines = output.split('\n')
        
        status = {"machines": "0", "state": "unknown"}
        for line in lines:
            if "Machines" in line and "running" in line.lower():
                # Extract running machine count
                if "0 running" in line:
                    status["machines"] = "0"
                    status["state"] = "stopped"
                elif "1 running" in line:
                    status["machines"] = "1" 
                    status["state"] = "running"
        
        return status
    
    def start_apps(self) -> None:
        """Start both apps for active use."""
        print("🚀 Starting Market Sim apps...")
        
        # Start web dashboard
        print(f"  Starting {self.web_app}...")
        self.run_command(["flyctl", "-a", self.web_app, "scale", "count", "1"])
        
        # Start bot
        print(f"  Starting {self.bot_app}...")
        self.run_command(["flyctl", "-a", self.bot_app, "scale", "count", "1"])
        
        # Wait for startup
        print("  Waiting for apps to start...")
        time.sleep(10)
        
        # Check status
        web_status = self.get_app_status(self.web_app)
        bot_status = self.get_app_status(self.bot_app)
        
        print(f"✅ Web Dashboard: {web_status['state']}")
        print(f"✅ Discord Bot: {bot_status['state']}")
        print("\n📊 Your apps are running! Remember to stop them when done to save costs.")
    
    def stop_apps(self) -> None:
        """Stop both apps to minimize costs."""
        print("⏹️  Stopping Market Sim apps to save costs...")
        
        # Stop web dashboard
        print(f"  Stopping {self.web_app}...")
        self.run_command(["flyctl", "-a", self.web_app, "scale", "count", "0"])
        
        # Stop bot  
        print(f"  Stopping {self.bot_app}...")
        self.run_command(["flyctl", "-a", self.bot_app, "scale", "count", "0"])
        
        print("✅ Apps stopped. No charges will accrue while stopped.")
        print("💡 Run with --start to restart when needed.")
    
    def status(self) -> None:
        """Show current status of both apps."""
        print("📊 Market Sim App Status:")
        print("=" * 40)
        
        web_status = self.get_app_status(self.web_app)
        bot_status = self.get_app_status(self.bot_app)
        
        print(f"Web Dashboard ({self.web_app}):")
        print(f"  State: {web_status['state']}")
        print(f"  Machines: {web_status['machines']}")
        
        print(f"\nDiscord Bot ({self.bot_app}):")
        print(f"  State: {bot_status['state']}")
        print(f"  Machines: {bot_status['machines']}")
        
        # Cost estimate
        running_count = 0
        if web_status['machines'] == "1":
            running_count += 1
        if bot_status['machines'] == "1":
            running_count += 1
            
        if running_count == 0:
            print(f"\n💰 Current cost: $0/month (all stopped)")
        else:
            estimated_monthly = running_count * 5.69  # Approx cost for shared-cpu-1x
            print(f"\n💰 Estimated monthly cost: ~${estimated_monthly:.2f}")
            print("   💡 Stop apps when not in use to minimize costs")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Fly.io Cost Manager for Market Sim")
        print("\nUsage:")
        print("  python fly_manager.py start   # Start both apps")
        print("  python fly_manager.py stop    # Stop both apps") 
        print("  python fly_manager.py status  # Show current status")
        return
    
    manager = FlyManager()
    command = sys.argv[1].lower()
    
    if command == "start":
        manager.start_apps()
    elif command == "stop":
        manager.stop_apps()
    elif command == "status":
        manager.status()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: start, stop, status")

if __name__ == "__main__":
    main()
