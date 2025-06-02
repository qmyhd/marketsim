# 📈 Market Sim - Discord Trading Game Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3+-blue.svg)](https://discordpy.readthedocs.io/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Fly.io](https://img.shields.io/badge/Deploy-Fly.io-purple.svg)](https://fly.io/)

A comprehensive Discord bot for simulating stock trading with real market data, portfolio tracking, and web dashboard. Perfect for learning trading concepts, competing with friends, and practicing investment strategies in a risk-free environment.

## ✨ Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/Market_sim.git
cd Market_sim

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the bot
python start_bot.py

# Run the web dashboard (optional)
python start_dashboard.py
```

**🎯 Key Features**: Real-time stock prices • Portfolio tracking • Web dashboard • Leaderboards • $1M starting capital • Educational focus

## 🚀 Features

### Discord Bot Commands

#### **Trading Commands**
- `!join` - Join the trading game with $1,000,000 starting capital
  - Creates new user account if doesn't exist
  - Sets initial portfolio value for ROI calculations
  - One-time setup per Discord user

- `!balance` - Check your current cash balance
  - Shows available cash for purchases
  - Displays in formatted currency ($X,XXX,XXX.XX)

- `!buy <symbol> <quantity>` - Buy stocks by share quantity
  - Example: `!buy AAPL 100` (buy 100 shares of Apple)
  - Validates sufficient cash and real stock symbol
  - Updates holdings with weighted average cost basis

- `!USD <symbol> <amount>` - Buy stocks with dollar amount
  - Example: `!USD TSLA 5000` (buy $5,000 worth of Tesla)
  - Automatically calculates shares based on current price
  - Useful for percentage-based portfolio allocation

- `!sell <symbol> <quantity>` - Sell stocks
  - Example: `!sell GOOGL 50` (sell 50 shares of Google)
  - Validates sufficient shares owned
  - Calculates realized P&L at time of sale

#### **Portfolio & Analytics Commands**
- `!portfolio` - View your complete portfolio with P&L
  - Shows cash balance and all stock positions
  - Displays current value, cost basis, and unrealized P&L
  - Includes total portfolio value and ROI percentage

- `!leaderboard` - See top traders ranked by ROI
  - Shows top 10 users by return on investment
  - Displays portfolio values and performance metrics
  - Updates in real-time with current market prices

- `!chart` - Generate portfolio performance chart
  - Creates matplotlib visualization of portfolio value over time
  - Shows historical performance vs starting value
  - Uploaded as image directly to Discord channel

### Web Dashboard

#### **Main Dashboard Features** (http://localhost:8080)
- **Real-time Leaderboard**: Sortable table showing all traders
  - Columns: Rank, Username, Cash, Holdings Value, Total Value, ROI
  - Click column headers to sort by any metric
  - Color-coded positive/negative returns

- **Market Summary Statistics**:
  - Total Assets Under Management (AUM)
  - Average ROI across all users
  - Best performing trader
  - Number of active traders

- **Live Data Integration**:
  - Real-time stock prices from Finnhub API
  - Auto-refresh every 30 seconds
  - Current market status indicators

#### **Individual Portfolio Pages** (http://localhost:8080/user/{user_id})
- **Portfolio Overview Dashboard**:
  - Cash balance, holdings value, total value
  - ROI calculation and performance metrics
  - Last update timestamp

- **Interactive Visualizations**:
  - **Pie Chart**: Portfolio allocation by stock position
  - **Line Chart**: Historical performance over time
  - **Holdings Table**: Detailed breakdown with P&L

- **Responsive Design**:
  - Mobile-optimized layout
  - Bootstrap 5 styling with dark theme
  - Font Awesome icons and smooth animations

### Key System Features

#### **Real-time Market Data**
- Powered by Finnhub API for accurate pricing
- Company name resolution for better UX
- Market status awareness (open/closed)
- Rate limiting and error handling

#### **Portfolio Value Tracking**
- Continuous portfolio valuation using live prices
- Historical data preservation for trend analysis
- ROI calculations based on individual starting values
- Daily snapshots for performance charting

#### **Automated Daily Updates**
- Scheduled portfolio updates at 6 PM daily
- Automatic total value calculations
- Historical data preservation in database
- Maintains data integrity across market closures

#### **Comprehensive P&L Calculations**
- Position-level P&L: (current_price - avg_price) × shares
- Portfolio-level ROI: (current_value - initial_value) / initial_value
- Realized vs unrealized gains tracking
- Cost basis updates with new purchases

#### **User Experience Enhancements**
- Company name display alongside ticker symbols
- Formatted currency display ($X,XXX,XXX.XX)
- Error handling with helpful user feedback
- Input validation for all trading commands

## 📁 Project Structure

### Core Application Files

#### **`botsim_enhanced.py`** - Main Discord Bot
The heart of the trading simulation featuring:
- **Discord command handlers**: All trading commands (`!buy`, `!sell`, `!portfolio`, etc.)
- **Database operations**: User management, transaction processing, portfolio calculations
- **Real-time market data**: Finnhub API integration for live stock prices
- **Scheduled tasks**: Daily portfolio updates via APScheduler
- **Error handling**: Comprehensive validation and user feedback

#### **`dashboard_robinhood.py`** - Web Dashboard
Modern Flask-based web interface providing:
- **Leaderboard**: Sortable table with ROI rankings and portfolio values
- **Individual portfolios**: Detailed user pages with interactive charts
- **Real-time data**: Live stock prices and portfolio calculations
- **Responsive UI**: Bootstrap 5 with dark theme and animations
- **API endpoints**: JSON data for dynamic content updates

#### **`start_bot.py`** & **`start_dashboard.py`** - Easy Launchers
Simplified startup scripts that:
- Handle environment variable loading
- Provide clear error messages for missing dependencies
- Offer convenient single-command startup for development
- Include basic validation before launching main applications

### Database & Utilities

#### **`fix_schema.py`** - Database Maintenance
Essential utility for:
- Schema migrations and updates
- Data integrity checks and repairs
- Adding new columns to existing tables
- Fixing inconsistencies in user data

#### **`update_capital.py`** - Capital Management
Administrative tool for:
- Adjusting starting capital for all users
- Bulk portfolio resets
- Historical data preservation during capital changes
- ROI recalculation after adjustments

#### **`validate.py`** - Pre-deployment Validation
Comprehensive testing script that verifies:
- Database connectivity and schema integrity
- API key validity (Discord, Finnhub)
- Environment variable completeness
- File permissions and directory structure

#### **`trading_game.db`** - SQLite Database
Persistent storage containing:
- **users table**: Discord IDs, cash balances, initial values, last calculated values
- **holdings table**: Stock positions with symbols, shares, average prices
- **history table**: Daily portfolio snapshots for performance tracking

### Configuration Files

#### **`requirements.txt`** - Python Dependencies
Key packages include:
- `discord.py` - Discord bot framework
- `aiosqlite` - Async SQLite operations
- `flask` - Web dashboard backend
- `aiohttp` - HTTP client for API calls
- `apscheduler` - Task scheduling
- `matplotlib` - Chart generation

#### **`.env`** & **`.env.example`** - Environment Variables
Critical configuration:
- `TOKEN` - Discord bot authentication token
- `FINNHUB_API_KEY` - Real-time market data access
- `DISCORD_CHANNEL_ID` - Target channel for bot operations

### Deployment Files

#### **`Dockerfile`** & **`Dockerfile.bot`** - Container Configurations
- **Dockerfile**: Web dashboard container (Flask app on port 8080)
- **Dockerfile.bot**: Discord bot container (background service)
- Both optimized for Python 3.11 with minimal Alpine Linux base

#### **`fly.toml`** & **`fly.bot.toml`** - Fly.io Configurations
- **fly.toml**: Web service configuration with health checks
- **fly.bot.toml**: Bot service configuration for background operation
- Includes volume mounts for database persistence

#### **`FLY.md`** - Deployment Guide
Comprehensive deployment instructions covering:
- Fly.io setup and authentication
- Environment variable configuration
- Database volume management
- Scaling and monitoring

#### **`DEPLOYMENT_CHECKLIST.md`** - Step-by-step Guide
Pre-deployment verification including:
- Code review checkpoints
- Environment setup validation
- Testing procedures
- Go-live checklist

### Documentation Files

#### **`README.md`** - Main Documentation
This comprehensive guide covering all aspects of the project.

#### **`DASHBOARD_README.md`** - Dashboard-specific Documentation
Detailed dashboard documentation including:
- Feature descriptions and screenshots
- Technical implementation details
- Customization options
- API endpoint documentation

## 🛠 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Key Dependencies Installed:**
- `discord.py` - Discord bot framework with async support
- `aiosqlite` - Asynchronous SQLite database operations
- `flask` - Web framework for the dashboard
- `aiohttp` - HTTP client for API requests
- `apscheduler` - Task scheduling for daily updates
- `matplotlib` - Chart generation for portfolio visualizations
- `python-dotenv` - Environment variable management

### 2. Environment Variables
Create a `.env` file (you can copy from `.env.example`) with:
```env
TOKEN=your_discord_bot_token
FINNHUB_API_KEY=your_finnhub_api_key
DISCORD_CHANNEL_ID=your_discord_channel_id
```

**How to Obtain Required Keys:**

#### Discord Bot Token
1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the token (keep this secret!)
5. Enable necessary bot permissions:
   - Send Messages
   - Read Message History
   - Use Slash Commands

#### Finnhub API Key
1. Sign up at [Finnhub.io](https://finnhub.io/)
2. Get your free API key from the dashboard
3. Free tier includes 60 API calls/minute (sufficient for most use cases)

#### Discord Channel ID
1. Enable Developer Mode in Discord (User Settings > Advanced)
2. Right-click your target channel
3. Select "Copy ID"

### 3. Database Initialization
The bot automatically creates the SQLite database on first run:
```bash
# The database file will be created as 'trading_game.db'
# No manual setup required - schema is auto-generated
```

### 4. Run the Bot
```bash
# Easy way (recommended)
python start_bot.py

# Direct way
python botsim_enhanced.py
```

**Bot Startup Process:**
1. Loads environment variables from `.env`
2. Connects to Discord API
3. Initializes SQLite database (creates tables if needed)
4. Sets up scheduled tasks for daily portfolio updates
5. Registers command handlers
6. Reports successful startup to console

### 5. Run the Dashboard (Optional)
```bash
# Easy way (recommended)  
python start_dashboard.py

# Direct way
python dashboard_robinhood.py
```

**Dashboard Features:**
- Visit http://localhost:8080 for the web interface
- Real-time leaderboard with sortable columns
- Individual portfolio pages at `/user/{user_id}`
- Responsive design that works on mobile devices
- Auto-refresh functionality for live data updates

### 6. First-Time Setup Verification
```bash
# Run the validation script
python validate.py
```

**This script checks:**
- Database connectivity
- API key validity
- Required file permissions
- Environment variable completeness

## 🗄 Database Schema

The bot uses SQLite (`trading_game.db`) with three main tables:

### **`users` Table**
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,        -- Discord user ID
    cash REAL DEFAULT 1000000,      -- Available cash balance
    initial_value REAL DEFAULT 1000000,  -- Starting portfolio value
    last_value REAL                 -- Last calculated total value
);
```
**Purpose**: Tracks user accounts, cash balances, and portfolio baselines for ROI calculations.

### **`holdings` Table**
```sql
CREATE TABLE holdings (
    user_id TEXT,                    -- Discord user ID (foreign key)
    symbol TEXT,                     -- Stock ticker symbol
    shares REAL,                     -- Number of shares owned
    avg_price REAL,                  -- Average cost basis per share
    PRIMARY KEY (user_id, symbol)
);
```
**Purpose**: Stores current stock positions with cost basis for P&L calculations.

### **`history` Table**
```sql
CREATE TABLE history (
    user_id TEXT,                    -- Discord user ID (foreign key)
    date TEXT,                       -- Date in YYYY-MM-DD format
    total_value REAL,                -- Total portfolio value on date
    PRIMARY KEY (user_id, date)
);
```
**Purpose**: Daily snapshots of portfolio values for performance charts and historical tracking.

### **Database Operations**

#### **User Management**
- New users automatically added with `!join` command
- Initial capital set to $1,000,000 by default
- User IDs are Discord snowflake IDs (unique 64-bit integers)

#### **Transaction Processing**
- Buy orders: Deduct cash, add/update holdings
- Sell orders: Add cash, reduce/remove holdings
- Automatic validation prevents overselling
- Real-time price fetching during transactions

#### **Portfolio Calculations**
- Total value = cash + (shares × current_price) for all holdings
- ROI = (current_value - initial_value) / initial_value × 100
- P&L = (current_price - avg_price) × shares for each position

#### **Daily Updates**
- Scheduled task runs daily at 6 PM (APScheduler)
- Updates `last_value` in users table
- Adds new records to history table
- Preserves historical data for chart generation

## 🔧 Configuration & Architecture

### **Application Architecture**

#### **Asynchronous Design**
- **Discord Bot**: Built on `discord.py` with async/await patterns
- **Database Operations**: `aiosqlite` for non-blocking database access
- **HTTP Requests**: `aiohttp` for concurrent API calls
- **Task Scheduling**: `APScheduler` for background operations

#### **Data Flow**
```
Discord User Command → Bot Handler → Database Update → API Price Fetch → Response
                                                    ↓
Web Dashboard ← Database Query ← Real-time Price Updates ← Finnhub API
```

#### **Service Communication**
- **Shared Database**: SQLite file accessible to both services
- **Independent Scaling**: Bot and web services can scale separately
- **State Management**: Database serves as single source of truth
- **Real-time Sync**: Both services read live data for consistency

### **Configuration Management**

#### **Starting Capital Configuration**
```python
# Default starting capital: $1,000,000
# Modify in botsim_enhanced.py, line ~50
DEFAULT_STARTING_CASH = 1000000

# Update existing users with new capital
python update_capital.py
```

#### **Scheduled Task Timing**
```python
# Daily portfolio updates at 6 PM Eastern
# Modify in botsim_enhanced.py
scheduler.add_job(
    daily_update,
    'cron',
    hour=18,  # 6 PM
    minute=0,
    timezone='US/Eastern'
)
```

#### **API Rate Limiting**
- **Finnhub Free Tier**: 60 calls/minute
- **Bot Implementation**: Built-in rate limiting and error handling
- **Fallback Strategy**: Cached prices for temporary API failures
- **Production Consideration**: Upgrade to paid tier for higher volume

#### **Port Configuration**
```python
# Web Dashboard - Fly.io compatible
port = int(os.getenv("PORT", 8080))  # Uses Fly.io's PORT or defaults to 8080

# Local Development
python start_dashboard.py  # Always uses port 8080 locally
```

### **Security Features**

#### **Environment Variable Management**
- **No Hardcoded Secrets**: All sensitive data in `.env` file
- **Git Ignore**: `.env` file excluded from version control
- **Example Template**: `.env.example` provides safe template
- **Production Deployment**: Secrets managed via Fly.io secrets

#### **Database Security**
- **Local File Access**: SQLite database file permissions
- **No External Exposure**: Database not accessible via network
- **Backup Strategy**: Regular file backups recommended for production
- **Data Validation**: Input sanitization for all user commands

#### **API Key Protection**
```python
# Secure loading pattern used throughout
load_dotenv()
API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    raise ValueError("FINNHUB_API_KEY environment variable required")
```

## 📊 API Integration & Data Sources

### **Finnhub API Integration**
The application integrates with Finnhub for real-time market data:

#### **Supported Endpoints**
- **Quote API**: `/api/v1/quote` - Real-time stock prices
- **Company Profile**: `/api/v1/stock/profile2` - Company information
- **Response Format**: JSON with current price, change, and metadata

#### **Error Handling Strategy**
```python
async def get_price(symbol):
    try:
        # Primary API call
        response = await session.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}")
        data = await response.json()
        return data.get('c')  # Current price
    except:
        # Fallback to last known price or return None
        return get_cached_price(symbol)
```

#### **Rate Limiting Implementation**
- Automatic retry with exponential backoff
- Request queuing during high-volume periods
- Graceful degradation when API limits exceeded
- User feedback for temporary service unavailability

### **Discord API Integration**
Built on the robust `discord.py` library:

#### **Bot Permissions Required**
- `Send Messages` - Respond to user commands
- `Read Message History` - Process commands in context
- `Embed Links` - Send rich formatted responses
- `Attach Files` - Upload portfolio charts

#### **Command Processing Flow**
1. User sends command in Discord channel
2. Bot validates command syntax and parameters
3. Database operations performed (buy/sell/query)
4. Real-time price fetching if needed
5. Response formatted and sent to channel
6. Error handling with user-friendly messages

## 🚀 Deployment Guide

### **Local Development Setup**

#### **Prerequisites**
- Python 3.11 or higher
- Git for version control
- Discord account and server admin access
- Finnhub account for API access

#### **Step-by-Step Local Setup**
```bash
# 1. Clone and setup
git clone https://github.com/your-username/Market_sim.git
cd Market_sim

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your actual API keys

# 5. Test the setup
python validate.py

# 6. Run the bot
python start_bot.py

# 7. Run dashboard (separate terminal)
python start_dashboard.py
```

### **Production Deployment on Fly.io**

#### **Why Fly.io?**
- **Global Edge Network**: Low latency worldwide
- **SQLite Support**: Persistent volumes for database storage
- **Dual Service Architecture**: Separate web and bot deployments
- **Environment Variables**: Secure secret management
- **Zero Downtime Deploys**: Rolling updates with health checks

#### **Deployment Architecture**
```
┌─────────────────┐    ┌─────────────────┐
│   Web Service   │    │   Bot Service   │
│ (dashboard)     │    │ (Discord bot)   │
│ Port: 8080      │    │ Background      │
│ HTTP Endpoints  │    │ Task Scheduler  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────┬─────────┬─────┘
                 │         │
           ┌─────▼─────────▼─────┐
           │   SQLite Database   │
           │  (Persistent Volume) │
           └─────────────────────┘
```

#### **Complete Deployment Process**
Refer to `DEPLOYMENT_CHECKLIST.md` for the complete step-by-step guide:

1. **Fly.io Setup**
   ```bash
   # Install Fly CLI
   iwr https://fly.io/install.ps1 -useb | iex
   flyctl auth login
   ```

2. **Deploy Web Dashboard**
   ```bash
   flyctl launch --name market-sim-web
   flyctl deploy
   ```

3. **Deploy Discord Bot**
   ```bash
   # Temporarily use bot config
   cp fly.bot.toml fly.toml
   flyctl launch --name market-sim-bot
   flyctl deploy
   git checkout fly.toml  # Restore original config
   ```

4. **Configure Secrets**
   ```bash
   # Web service
   flyctl -a market-sim-web secrets set FINNHUB_API_KEY=your_key

   # Bot service  
   flyctl -a market-sim-bot secrets set TOKEN=your_token
   flyctl -a market-sim-bot secrets set FINNHUB_API_KEY=your_key
   flyctl -a market-sim-bot secrets set DISCORD_CHANNEL_ID=your_channel
   ```

## 🎯 Usage Examples

### **Common Trading Workflows**

#### **Getting Started (New User)**
```
!join                    # Join with $1,000,000 starting capital
!balance                 # Check initial cash: $1,000,000.00
!buy AAPL 100           # Buy 100 shares of Apple
!portfolio              # View updated portfolio
```

#### **Dollar-Based Investing**
```
!USD TSLA 10000         # Invest $10,000 in Tesla
!USD GOOGL 15000        # Invest $15,000 in Google
!USD MSFT 5000          # Invest $5,000 in Microsoft
!portfolio              # See diversified portfolio
```

#### **Portfolio Management**
```
!portfolio              # Check current positions
!sell AAPL 50          # Sell half of Apple position
!buy NVDA 25           # Buy Nvidia with proceeds
!leaderboard           # See how you rank
!chart                 # Generate performance chart
```

### **Web Dashboard Navigation**

#### **Main Dashboard Features**
- **URL**: http://localhost:8080 (local) or your-app.fly.dev (production)
- **Leaderboard**: Click column headers to sort by different metrics
- **Refresh**: Auto-refresh every 30 seconds or click refresh button
- **Portfolio Links**: Click "View Portfolio" for detailed user pages

#### **Individual Portfolio Analysis**
- **URL Pattern**: `/user/{discord_user_id}`
- **Charts**: Interactive pie chart (allocation) and line chart (performance)
- **Holdings Table**: Detailed P&L analysis for each position
- **Mobile Responsive**: Works on all device sizes

## 🐛 Troubleshooting & FAQ

### **Common Issues**

#### **Bot Won't Start**
```bash
# Check environment variables
python validate.py

# Common fixes:
# 1. Verify .env file exists and has correct keys
# 2. Check Discord token is valid (regenerate if needed)
# 3. Ensure bot has proper permissions in Discord server
# 4. Verify Python version (3.11+ required)
```

#### **API Errors**
- **"Invalid symbol"**: Stock ticker doesn't exist or is delisted
- **"Rate limit exceeded"**: Too many API calls, wait 1 minute
- **"Insufficient funds"**: Not enough cash for purchase
- **"Insufficient shares"**: Trying to sell more shares than owned

#### **Dashboard Issues**
```bash
# Dashboard won't load
python start_dashboard.py  # Check for error messages
# Common fixes:
# 1. Port 8080 might be in use (check with netstat)
# 2. Database file permissions
# 3. Missing Finnhub API key
```

#### **Database Issues**
```bash
# Reset database if corrupted
rm trading_game.db  # Warning: Deletes all data!
python start_bot.py  # Creates fresh database

# Fix schema issues
python fix_schema.py
```

### **Performance Optimization**

#### **For High-Volume Usage**
- Upgrade to Finnhub paid plan for higher API limits
- Consider PostgreSQL for better concurrent access
- Implement Redis caching for frequently accessed data
- Use connection pooling for database operations

#### **Memory Management**
- SQLite database grows over time with history data
- Consider archiving old historical data (>1 year)
- Monitor log files and implement rotation
- Use process monitoring tools for production

### **Best Practices**

#### **For Bot Administrators**
- Regularly backup the SQLite database file
- Monitor API usage to avoid rate limits
- Set up logging for error tracking
- Test all commands after updates

#### **For Server Moderators**
- Create dedicated trading channel
- Set clear rules about virtual trading
- Monitor for spam or abuse of commands
- Consider limiting access to specific roles

## 📈 Future Enhancements & Roadmap

### **Planned Features**
- **Options Trading**: Calls and puts simulation
- **Cryptocurrency Support**: Bitcoin, Ethereum, and altcoins
- **Advanced Charting**: Technical indicators and overlays
- **Social Features**: Following other traders, sharing strategies
- **Paper Trading Competitions**: Timed contests with prizes
- **Mobile App**: React Native companion app
- **Advanced Analytics**: Sharpe ratio, beta calculation, sector analysis

### **Technical Improvements**
- **PostgreSQL Migration**: Better concurrent access and scalability
- **Redis Caching**: Faster response times and reduced API calls
- **GraphQL API**: More efficient data fetching for dashboard
- **WebSocket Integration**: Real-time portfolio updates
- **Microservices Architecture**: Separate services for different functions

### **Educational Features**
- **Trading Tutorials**: Interactive guides for beginners
- **Market News Integration**: Real-time financial news feeds
- **Economic Calendar**: Important events and earnings dates
- **Risk Management Tools**: Stop-loss and take-profit orders
- **Portfolio Analytics**: Risk metrics and performance attribution

## 🤝 Contributing

### **Development Setup**
```bash
# Fork the repository on GitHub
git clone https://github.com/your-username/Market_sim.git
cd Market_sim

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
python validate.py
python start_bot.py  # Test bot functionality
python start_dashboard.py  # Test web interface

# Commit and push
git add .
git commit -m "Add your feature description"
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### **Code Style Guidelines**
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings for all functions
- Include error handling for all external API calls
- Write unit tests for new features

### **Testing**
```bash
# Run validation suite
python validate.py

# Test specific components
python -c "from botsim_enhanced import get_price; print(get_price('AAPL'))"

# Check database integrity
python fix_schema.py --check-only
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Finnhub.io** - Real-time market data API
- **Discord.py** - Python Discord API wrapper
- **Flask** - Web framework for dashboard
- **Chart.js** - Interactive charting library
- **Bootstrap** - UI framework for responsive design
- **Fly.io** - Cloud deployment platform

## 📞 Support

### **Getting Help**
- 📖 **Documentation**: Start with this README and `DASHBOARD_README.md`
- 🐛 **Issues**: Report bugs on [GitHub Issues](https://github.com/your-username/Market_sim/issues)
- 💬 **Discussions**: Join discussions on [GitHub Discussions](https://github.com/your-username/Market_sim/discussions)
- 📧 **Email**: Contact maintainers directly for security issues

### **Quick Links**
- [Deployment Guide](FLY.md) - Complete deployment instructions
- [Dashboard Documentation](DASHBOARD_README.md) - Web interface details
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) - Pre-deployment verification

---

**⭐ Star this repository if you find it useful!**

**📢 Share with friends to start your own trading competition!**

Made with ❤️ for the trading and Discord communities.

*Disclaimer: This is a simulation tool for educational purposes only. No real money or actual trading occurs. Always consult with financial professionals for actual investment decisions.*
