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
flyctl secrets set FINNHUB_API_KEY=your_finnhub_api_key

# For bot app only  
flyctl secrets set TOKEN=your_discord_bot_token
flyctl secrets set DISCORD_CHANNEL_ID=your_discord_channel_id
```

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
flyctl -a market-sim-web secrets set FINNHUB_API_KEY=your_key

# Bot app  
flyctl -a market-sim-bot secrets set TOKEN=your_token
flyctl -a market-sim-bot secrets set FINNHUB_API_KEY=your_key
flyctl -a market-sim-bot secrets set DISCORD_CHANNEL_ID=your_channel_id
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

# Scale apps
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

## Troubleshooting

### Common Issues
- **App won't start**: Check environment variables are set
- **Database errors**: Ensure database file permissions are correct
- **Port binding**: Verify PORT environment variable and internal_port match
- **Discord bot offline**: Check TOKEN and permissions

### Getting Help
```bash
# Check app configuration
flyctl -a your-app-name config show

# SSH into running app for debugging
flyctl -a your-app-name ssh console

# View resource usage
flyctl -a your-app-name vm status
```
