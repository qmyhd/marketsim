# 📈 Market Sim - Discord Trading Game Bot

A comprehensive Discord bot for simulating stock trading with real market data, portfolio tracking, and web dashboard.

## 🚀 Features

### Discord Bot Commands
- `!join` - Join the trading game with $1,000,000 starting capital
- `!balance` - Check your current cash balance
- `!buy <symbol> <quantity>` - Buy stocks by share quantity
- `!USD <symbol> <amount>` - Buy stocks with dollar amount
- `!sell <symbol> <quantity>` - Sell stocks
- `!portfolio` - View your complete portfolio with P&L
- `!leaderboard` - See top traders ranked by ROI
- `!chart` - Generate portfolio performance chart

### Web Dashboard
- Real-time leaderboard with sortable data
- Individual portfolio pages with interactive charts
- Market summary statistics
- Modern dark theme UI (Robinhood-inspired)

### Key Features
- Real-time stock prices via Finnhub API
- Portfolio value tracking with historical data
- Daily automated portfolio updates
- Comprehensive P&L calculations
- Company name display for better UX

## 📁 Project Structure

### Essential Files
- `botsim_enhanced.py` - Main Discord bot with all trading commands
- `dashboard_robinhood.py` - Web dashboard with modern UI
- `start_bot.py` - Easy launcher for the Discord bot
- `start_dashboard.py` - Easy launcher for the web dashboard
- `fix_schema.py` - Database maintenance utility
- `update_capital.py` - Capital adjustment utility
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API keys, tokens)
- `trading_game.db` - SQLite database with user data

### Supporting Files
- `README.md` - This documentation
- `DASHBOARD_README.md` - Dashboard-specific documentation
- `.gitignore` - Git ignore rules

## 🛠 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create/update `.env` file with:
```env
TOKEN=your_discord_bot_token
FINNHUB_API_KEY=your_finnhub_api_key
DISCORD_CHANNEL_ID=your_discord_channel_id
```

### 3. Run the Bot
```bash
# Easy way (recommended)
python start_bot.py

# Direct way
python botsim_enhanced.py
```

### 4. Run the Dashboard (Optional)
```bash
# Easy way (recommended)  
python start_dashboard.py

# Direct way
python dashboard_robinhood.py
```
Visit http://localhost:5001 for the web interface.

## 🗄 Database Schema

The bot uses SQLite with three main tables:
- `users` - User accounts with cash, initial_value, last_value
- `holdings` - Stock positions with shares and average price
- `history` - Daily portfolio value snapshots

## 🔧 Configuration

### Starting Capital
- New users receive $1,000,000 in virtual cash
- Historical users maintain their existing balance structure
- All ROI calculations use individual initial_value from database

### Scheduled Updates
- Daily portfolio updates at 6 PM
- Automatic portfolio value calculations
- Historical data preservation

## 🔐 Security Features
- No hardcoded API keys or tokens
- All secrets managed via environment variables
- Secure database access patterns

## 📊 API Integration
- **Finnhub API**: Real-time stock quotes and company information
- **Discord API**: Bot commands and automated messaging
- **Flask**: Web dashboard backend

## 🚀 Deployment Notes
- Compatible with cloud platforms (Heroku, Railway, etc.)
- SQLite database persists user data
- Environment variables required for production
- Automated daily tasks via APScheduler

## 🐛 Troubleshooting
- Ensure all environment variables are properly set
- Check Discord bot permissions for message sending
- Verify Finnhub API key has sufficient quota
- Database file must be writable by the application

## 📈 Future Enhancements
- Options trading simulation
- Crypto currency support
- Advanced charting features
- Social trading features
- Paper trading competitions
