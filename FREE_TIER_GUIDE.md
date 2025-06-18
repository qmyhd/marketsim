# 💰 Free Tier Deployment Guide for Fly.io

## 🎯 **Goal: Stay on Fly.io Free Tier ($0/month)**

This guide ensures your Market Sim bot runs efficiently while staying within Fly.io's free tier limits.

### **Free Tier Limits:**
- **$5/month credit** (renewable)
- **3 shared-cpu-1x machines** (256MB RAM each)
- **3GB persistent volume storage**
- **160GB outbound data transfer**

## 🚀 **Optimized Deployment Steps**

### 1. **Initial Setup (One-time)**

```powershell
# Install Fly CLI
iwr https://fly.io/install.ps1 -useb | iex

# Login to Fly.io
flyctl auth login

# Deploy web dashboard (will auto-create volume)
flyctl launch --name market-sim-web --no-deploy
flyctl deploy

# Deploy Discord bot
flyctl launch --name market-sim-bot --config fly.bot.toml --no-deploy
flyctl deploy
```

### 2. **Set Environment Variables**

```powershell
# Web dashboard secrets
flyctl -a market-sim-web secrets set FINNHUB_API_KEY="your_finnhub_key"
flyctl -a market-sim-web secrets set FINNHUB_API_KEY_SECOND="your_backup_key"
flyctl -a market-sim-web secrets set DATABASE_URL="/data/trading_game.db"

# Bot secrets
flyctl -a market-sim-bot secrets set TOKEN="your_discord_token"
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY="your_finnhub_key"
flyctl -a market-sim-bot secrets set DISCORD_CHANNEL_ID="your_channel_id"
flyctl -a market-sim-bot secrets set DISCORD_WEBHOOK_URL="your_webhook_url"
flyctl -a market-sim-bot secrets set BOT_COMMAND="daily_update"
flyctl -a market-sim-bot secrets set DATABASE_URL="/data/trading_game.db"
```

### 3. **Cost Management Strategy**

#### **Daily Usage Pattern (Recommended):**

```powershell
# Morning: Start apps when needed
python fly_manager.py start

# Evening: Stop apps to save money
python fly_manager.py stop

# Check status anytime
python fly_manager.py status
```

#### **Manual Control:**

```powershell
# Start for active use
flyctl -a market-sim-web scale count 1
flyctl -a market-sim-bot scale count 1

# Stop when done (CRITICAL for cost savings)
flyctl -a market-sim-web scale count 0
flyctl -a market-sim-bot scale count 0
```

## 💡 **Cost Optimization Tips**

### **Free Tier Best Practices:**

1. **Always Scale to 0**: When not actively using the bot
   ```powershell
   flyctl -a market-sim-web scale count 0
   flyctl -a market-sim-bot scale count 0
   ```

2. **Use Minimal Resources**: Both apps configured for 256MB RAM

3. **Regional Deployment**: Both apps in same region (iad) to share volume

4. **Automatic Scaling**: Apps auto-start on request, auto-stop when idle

5. **Monitor Usage**: Check monthly usage in Fly.io dashboard

### **Expected Monthly Costs:**

| Usage Pattern | Estimated Cost |
|---------------|----------------|
| **Stopped (0 machines)** | **$0.00** ✅ |
| **Light use (2-4 hours/day)** | **$1.50-3.00** ✅ |
| **Heavy use (8+ hours/day)** | **$4.00-5.00** ⚠️ |
| **Always running (24/7)** | **$11.38** ❌ |

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **"Volume not found"**:
   ```powershell
   flyctl volumes create trading_data --size 1 -a market-sim-web
   ```

2. **"App exceeding memory"**:
   ```powershell
   flyctl -a market-sim-web scale memory 512
   ```

3. **"Rate limit exceeded"**:
   - Add more Finnhub API keys to environment variables

4. **Check resource usage**:
   ```powershell
   flyctl -a market-sim-web vm status
   flyctl -a market-sim-bot vm status
   ```

## 📊 **Monitoring Free Tier Usage**

### **Check Monthly Limits:**

1. Visit [Fly.io Dashboard](https://fly.io/dashboard)
2. Go to "Billing" → "Usage"
3. Monitor:
   - **Machine hours** (should be <160 hrs/month for free)
   - **Data transfer** (should be <160GB/month)
   - **Storage** (should be <3GB)

### **Smart Usage Patterns:**

- **Weekend**: Scale to 0 completely
- **Weekday**: Start only when trading/testing
- **Vacation**: Keep everything at 0

## ✅ **Final Checklist**

- [ ] Both apps deployed with `min_machines_running = 0`
- [ ] All environment variables set
- [ ] Shared volume created and mounted
- [ ] `fly_manager.py` tested and working
- [ ] Apps start/stop properly via scaling commands
- [ ] Billing dashboard shows free tier usage

**Result**: Your Market Sim bot will run efficiently within Fly.io's free tier! 🎉

## 💰 **Pro Tip**: 
Set a phone reminder to run `python fly_manager.py stop` each evening to ensure you never accidentally leave apps running overnight.
