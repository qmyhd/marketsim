# Fly.io Deployment Configuration

This project is configured for deployment on Fly.io with separate applications for the web dashboard and Discord bot.

## Applications Architecture

### Web Dashboard App (`market-sim-web`)
- **Service**: Flask web dashboard (dashboard_robinhood.py)
- **Accessible**: Via HTTPS URL (public)
- **Port**: 8080 internally, 80/443 externally
- **Purpose**: Portfolio visualization and leaderboard

### Discord Bot App (`market-sim-bot`) 
- **Service**: Discord bot (botsim_enhanced.py)
- **Type**: Background worker (no web interface)
- **Purpose**: Trading commands and automated updates

## Environment Variables Required

Set these using `flyctl secrets set`:

```bash
# For both apps
flyctl secrets set FINNHUB_API_KEY=your_primary_finnhub_api_key

# Optional: Secondary Finnhub API keys for rate limit fallback
flyctl secrets set FINNHUB_API_KEY_SECOND=your_secondary_finnhub_api_key
flyctl secrets set FINNHUB_API_KEY_2=your_alternate_finnhub_api_key

# For bot app only  
flyctl secrets set TOKEN=your_discord_bot_token
flyctl secrets set DISCORD_CHANNEL_ID=your_discord_channel_id
```

### API Key Strategy
- **Primary Key**: `FINNHUB_API_KEY` - Main API key for all requests
- **Fallback Keys**: `FINNHUB_API_KEY_SECOND` and `FINNHUB_API_KEY_2` - Used when primary key hits rate limits
- **Free Tier Limits**: 60 calls/minute per key - multiple keys provide 120-180 calls/minute total
- **Automatic Fallback**: Bot automatically switches to secondary keys when rate limited

## Database Strategy

**Option 1: Shared Volume (Recommended for development)**
- Both apps mount the same volume for SQLite database
- Simple setup, but requires apps in same region

**Option 2: External Database (Recommended for production)**
- Use Fly.io Postgres or external database service
- Better for scaling and reliability
- Requires code changes to use PostgreSQL

## Deployment Commands

### Initial Setup
```bash
# Install Fly CLI
# Visit: https://fly.io/docs/getting-started/installing-flyctl/

# Login to Fly.io
flyctl auth login

# Create and deploy web dashboard
flyctl launch --name market-sim-web
flyctl deploy

# Create bot app (copy fly.toml and modify for bot)
flyctl launch --name market-sim-bot --no-deploy
# Edit fly.toml for bot configuration
flyctl deploy
```

### Setting Environment Variables
```bash
# Web dashboard app
flyctl -a market-sim-web secrets set FINNHUB_API_KEY=your_primary_key

# Optional fallback keys for web dashboard
flyctl -a market-sim-web secrets set FINNHUB_API_KEY_SECOND=your_secondary_key
flyctl -a market-sim-web secrets set FINNHUB_API_KEY_2=your_alternate_key

# Bot app - all environment variables
flyctl -a market-sim-bot secrets set TOKEN=your_token
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY=your_primary_key
flyctl -a market-sim-bot secrets set DISCORD_CHANNEL_ID=your_channel_id

# Optional fallback keys for bot
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY_SECOND=your_secondary_key
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY_2=your_alternate_key
```

### Managing Apps
```bash
# View apps
flyctl apps list

# Check app status
flyctl -a market-sim-web status
flyctl -a market-sim-bot status

# View logs
flyctl -a market-sim-web logs
flyctl -a market-sim-bot logs

# Scale apps to 1 instance (startup)
flyctl -a market-sim-web scale count 1
flyctl -a market-sim-bot scale count 1

# Scale apps to 0 instances (shutdown/cost saving)
flyctl -a market-sim-web scale count 0
flyctl -a market-sim-bot scale count 0

# Memory optimization (reduce from default 256MB to 256MB - confirmed working)
flyctl -a market-sim-web scale memory 256
flyctl -a market-sim-bot scale memory 256
```

### Cost Management
When not actively using the bot, scale both apps to zero to avoid charges:
```bash
# Before stopping for extended periods
flyctl -a market-sim-web scale count 0
flyctl -a market-sim-bot scale count 0

# When ready to use again
flyctl -a market-sim-web scale count 1
flyctl -a market-sim-bot scale count 1
```

## Database Deployment Notes

- SQLite database will be created automatically on first run
- Database persists in app's file system (ephemeral in Fly.io)
- For production, consider using Fly.io Postgres for persistence:

```bash
# Create a Postgres database
flyctl postgres create --name market-sim-db

# Attach to your apps
flyctl -a market-sim-web postgres attach market-sim-db
flyctl -a market-sim-bot postgres attach market-sim-db
```

## Recommended Deployment Workflow

### First-Time Setup
1. **Deploy both applications** following the Initial Setup commands above
2. **Set all environment variables** including multiple API keys
3. **Test functionality** with basic Discord commands
4. **Scale to zero** when not actively using to minimize costs

### Daily Usage Pattern
```bash
# Morning: Start both applications
flyctl -a market-sim-web scale count 1
flyctl -a market-sim-bot scale count 1

# Verify both are running
flyctl -a market-sim-web status
flyctl -a market-sim-bot status

# Evening: Stop both applications to save costs
flyctl -a market-sim-web scale count 0
flyctl -a market-sim-bot scale count 0
```

### Weekend/Extended Breaks
```bash
# Before leaving for extended periods
flyctl -a market-sim-web scale count 0
flyctl -a market-sim-bot scale count 0

# Check that instances are stopped
flyctl apps list
```

This workflow ensures minimal costs while maintaining full functionality when needed.

## Migration from Railway

Railway-specific files have been removed:
- `Procfile` - ✅ Removed (replaced by Dockerfile CMD)
- `RAILWAY.md` - ✅ Removed (replaced by this file)
- `runtime.txt` - ✅ Removed (specified in Dockerfile)

The application code requires minimal changes:
- Port handling already supports `PORT` environment variable
- Environment variables work the same way
- Database and API integrations unchanged

## Production Considerations

1. **Database**: Migrate to PostgreSQL for better persistence
2. **Monitoring**: Use Fly.io metrics and logging
3. **Scaling**: Configure auto-scaling based on usage
4. **Secrets**: Never commit API keys - always use `flyctl secrets`
5. **Regions**: Deploy close to your users for better performance
6. **API Rate Limits**: Use multiple Finnhub API keys for higher throughput
7. **Cost Optimization**: Scale to zero when inactive, use minimal memory settings

### Resource Optimization
The applications are configured for minimal resource usage:
- **Memory**: 256MB per instance (sufficient for SQLite + API calls)
- **CPU**: Shared CPU (1 core) - adequate for Discord bot workload
- **Scaling**: Manual scaling recommended (0-1 instances as needed)

### Multiple API Keys Setup
To maximize API throughput with Finnhub free tier:
1. Create 2-3 Finnhub accounts for additional API keys
2. Set all keys as environment variables (FINNHUB_API_KEY, FINNHUB_API_KEY_SECOND, FINNHUB_API_KEY_2)
3. Bot automatically rotates through available keys when rate limited
4. Total throughput: 60-180 API calls/minute (vs 60 with single key)

## Troubleshooting

### Common Issues
- **App won't start**: Check environment variables are set with `flyctl -a app-name secrets list`
- **Database errors**: Ensure database file permissions are correct
- **Port binding**: Verify PORT environment variable and internal_port match
- **Discord bot offline**: Check TOKEN and permissions
- **API rate limiting**: Ensure multiple FINNHUB_API_KEY variables are set
- **High costs**: Scale unused apps to 0 instances
- **Memory issues**: Apps optimized for 256MB, increase if needed

### API Key Troubleshooting
```bash
# Check which secrets are set (values hidden)
flyctl -a market-sim-bot secrets list
flyctl -a market-sim-web secrets list

# Set missing API keys
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY_SECOND=your_key
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY_2=your_key
```

### Getting Help
```bash
# Check app configuration
flyctl -a your-app-name config show

# SSH into running app for debugging
flyctl -a your-app-name ssh console

# View resource usage
flyctl -a your-app-name vm status
```
