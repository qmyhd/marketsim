# 🚀 Fly.io Deployment Checklist

## ✅ Migration Status - COMPLETE

### Railway Files Removed:
- [x] `Procfile` - ✅ Removed
- [x] `RAILWAY.md` - ✅ Removed  
- [x] `runtime.txt` - ✅ Removed

### Fly.io Files Ready:
- [x] `fly.toml` - ✅ Web dashboard configuration
- [x] `fly.bot.toml` - ✅ Discord bot configuration
- [x] `Dockerfile` - ✅ Web dashboard container
- [x] `Dockerfile.bot` - ✅ Discord bot container
- [x] `FLY.md` - ✅ Deployment documentation

### Application Code Status:
- [x] Port configuration - ✅ Properly configured for Fly.io
- [x] Environment variables - ✅ Using .env pattern
- [x] Database - ✅ SQLite database exists
- [x] Import statements - ✅ No errors detected
- [x] README.md - ✅ Updated to reference Fly.io

## 🚀 Deployment Steps

### 1. Install Fly CLI (if not already installed)
```powershell
# Install using PowerShell
iwr https://fly.io/install.ps1 -useb | iex
```

### 2. Login to Fly.io
```powershell
flyctl auth login
```

### 3. Deploy Web Dashboard
```powershell
# From your project directory
flyctl launch --name market-sim-web --generate-name false
flyctl deploy
```

### 4. Deploy Discord Bot
```powershell
# Copy bot config to main fly.toml for bot deployment
Copy-Item fly.bot.toml fly.toml
flyctl launch --name market-sim-bot --generate-name false
flyctl deploy
# Restore original fly.toml
git checkout fly.toml
```

### 5. Set Environment Variables
```powershell
# Web dashboard
flyctl -a market-sim-web secrets set FINNHUB_API_KEY=your_finnhub_api_key

# Discord bot
flyctl -a market-sim-bot secrets set TOKEN=your_discord_bot_token
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY=your_finnhub_api_key
flyctl -a market-sim-bot secrets set DISCORD_CHANNEL_ID=your_discord_channel_id
```

### 6. Verify Deployments
```powershell
# Check status
flyctl -a market-sim-web status
flyctl -a market-sim-bot status

# View logs
flyctl -a market-sim-web logs
flyctl -a market-sim-bot logs
```

## 📋 Pre-Deployment Checklist

- [ ] Fly CLI installed and authenticated
- [ ] Environment variables ready (TOKEN, FINNHUB_API_KEY, DISCORD_CHANNEL_ID)
- [ ] Git repository committed and pushed
- [ ] Tested locally with `python start_dashboard.py` and `python start_bot.py`

## 🔧 Post-Deployment

- [ ] Web dashboard accessible at Fly.io URL
- [ ] Discord bot online and responding to commands
- [ ] Database working (test with `!join` command)
- [ ] Scheduled tasks running (check daily updates)

## 📝 Notes

- App names can be customized during `flyctl launch`
- Both apps will be in the same region (iad - Washington D.C.)
- SQLite database will be created automatically
- For production, consider migrating to PostgreSQL

## 🆘 Troubleshooting

If issues occur:
1. Check app logs: `flyctl -a <app-name> logs`
2. Verify environment variables: `flyctl -a <app-name> secrets list`
3. SSH into app: `flyctl -a <app-name> ssh console`
4. Refer to `FLY.md` for detailed troubleshooting
