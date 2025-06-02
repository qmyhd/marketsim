# Railway Deployment Configuration

This project is configured for deployment on Railway.app with the following services:

## Services
- **web**: Dashboard service (dashboard_robinhood.py) - accessible via web URL
- **worker**: Discord bot service (botsim_enhanced.py) - background worker

## Environment Variables Required
Set these in Railway dashboard:
- `TOKEN` - Your Discord bot token
- `FINNHUB_API_KEY` - Your Finnhub API key
- `DISCORD_CHANNEL_ID` - Discord channel ID for updates

## Database
- Uses SQLite database file
- Database will be created automatically on first run
- No external database service required

## Deployment Notes
- Web service runs on port determined by Railway ($PORT environment variable)
- Worker service runs continuously in background
- Both services share the same SQLite database file
