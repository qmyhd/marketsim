# Market Sim - Complete Process Documentation

## 📋 Overview

This document provides comprehensive documentation of all processes, workflows, and procedures for the Market Sim Discord trading bot. It serves as a complete reference for development, deployment, maintenance, and troubleshooting.

## 🚀 Development Workflow

### Initial Setup Process

1. **Repository Setup**
   ```bash
   git clone https://github.com/your-username/Market_sim.git
   cd Market_sim
   ```

2. **Environment Preparation**
   ```bash
   # Create virtual environment (recommended)
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Mac/Linux
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configuration Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your API keys and settings
   # Required: TOKEN, FINNHUB_API_KEY
   # Optional: Additional API keys for fallbacks
   ```

4. **Database Initialization**
   ```bash
   # Database is automatically created on first run
   # No manual setup required - schema auto-generated
   ```

5. **Validation and Testing**
   ```bash
   # Run pre-deployment validation
   python validate_deployment.py
   
   # Test compilation of all Python files
   python -m py_compile *.py commands/*.py
   ```

### Development Commands

```bash
# Start Discord bot (development)
python start_bot.py

# Start web dashboard (development)
python start_dashboard.py

# Run validation suite
python validate_deployment.py

# Database maintenance
python fix_database_schema.py

# Fly.io deployment management
python fly_manager.py
```

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                Market Sim Architecture                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │   Discord    │    │     Web      │                 │
│  │     Bot      │    │  Dashboard   │                 │
│  │   Service    │    │   Service    │                 │
│  └──────┬───────┘    └──────┬───────┘                 │
│         │                   │                         │
│         └───────┬───────────┘                         │
│                 │                                     │
│         ┌───────▼───────┐                             │
│         │   SQLite DB   │                             │
│         │   (Shared)    │                             │
│         └───────────────┘                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           External APIs                         │   │
│  │  • Finnhub (Primary)                           │   │
│  │  • Polygon (Secondary)                         │   │
│  │  • Alpaca (Tertiary)                           │   │
│  │  • Yahoo Finance (Fallback)                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Process

1. **Command Processing Flow**
   ```
   Discord User → Bot Command → Validation → Database Update → API Call → Response
   ```

2. **Web Dashboard Flow**
   ```
   HTTP Request → Flask Route → Database Query → API Call → Template Render → Response
   ```

3. **Price Caching Flow**
   ```
   Price Request → Cache Check → API Call (if needed) → Cache Update → Database Persist
   ```

## 🗄️ Database Schema and Operations

### Table Structures

```sql
-- Users table: Core user account information
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,        -- Discord user ID
    cash REAL DEFAULT 1000000,      -- Available cash balance
    initial_value REAL DEFAULT 1000000,  -- Starting portfolio value
    last_value REAL DEFAULT 1000000,     -- Last calculated total value
    username TEXT                    -- Discord display name
);

-- Holdings table: Stock positions
CREATE TABLE holdings (
    user_id TEXT,                    -- Discord user ID (foreign key)
    symbol TEXT,                     -- Stock ticker symbol
    shares INTEGER,                  -- Number of shares owned (integer)
    avg_price REAL,                  -- Average cost basis per share
    PRIMARY KEY (user_id, symbol)
);

-- History table: Daily portfolio snapshots
CREATE TABLE history (
    user_id TEXT,                    -- Discord user ID (foreign key)
    date TEXT,                       -- Date in YYYY-MM-DD format
    portfolio_value REAL,           -- Total portfolio value on date
    PRIMARY KEY (user_id, date)
);

-- Last_price table: Cached stock prices
CREATE TABLE last_price (
    symbol TEXT PRIMARY KEY,        -- Stock ticker symbol
    price REAL,                     -- Last known price
    last_updated TEXT               -- Timestamp of last update
);
```

### Database Operations Process

1. **User Account Creation**
   - Check if user exists
   - Insert new user with default starting capital
   - Set initial_value for ROI calculations

2. **Trading Operations**
   - Validate sufficient funds/shares
   - Calculate new cost basis (weighted average)
   - Update cash and holdings atomically
   - Record transaction for audit trail

3. **Portfolio Calculation**
   - Fetch current holdings
   - Get real-time prices for all symbols
   - Calculate total value = cash + (shares × current_price)
   - Compute ROI = (current_value - initial_value) / initial_value

4. **Daily Updates**
   - Process all users
   - Update last_value in users table
   - Insert daily snapshot in history table
   - Maintain historical data for charting

## 🌐 API Integration Process

### Multi-Provider Strategy

```python
# API Priority Order
1. Finnhub (Primary) - Real-time data, rate limited
2. Finnhub Secondary Keys - Backup for rate limits
3. Polygon API - Alternative provider
4. Alpaca API - Financial data alternative
5. Yahoo Finance - Free fallback option
```

### Rate Limiting Process

1. **Request Throttling**
   - Minimum 2-second interval between API calls
   - Exponential backoff on 429 (rate limit) responses
   - Global rate limit tracking across all requests

2. **Caching Strategy**
   - In-memory cache with TTL (24 hours default)
   - LRU eviction when memory limits reached
   - Database persistence for cache durability

3. **Error Handling**
   - Graceful degradation to cached prices
   - Fallback to alternative API providers
   - User-friendly error messages

## 🚀 Deployment Process

### Local Development Deployment

1. **Environment Setup**
   ```bash
   # Ensure all dependencies installed
   pip install -r requirements.txt
   
   # Validate configuration
   python validate_deployment.py
   ```

2. **Start Services**
   ```bash
   # Terminal 1: Start Discord bot
   python start_bot.py
   
   # Terminal 2: Start web dashboard
   python start_dashboard.py
   ```

3. **Access Points**
   - Discord bot: Available in configured Discord server
   - Web dashboard: http://localhost:8080

### Production Deployment (Fly.io)

1. **Pre-deployment Checklist**
   ```bash
   # Run comprehensive validation
   python validate_deployment.py
   
   # Verify Fly.io CLI installed
   flyctl version
   
   # Authenticate with Fly.io
   flyctl auth login
   ```

2. **Deploy Web Service**
   ```bash
   # Use main configuration
   flyctl launch --name market-sim-web
   flyctl deploy
   
   # Set environment secrets
   flyctl secrets set FINNHUB_API_KEY=your_key
   flyctl secrets set DATABASE_URL=/data/trading_game.db
   ```

3. **Deploy Bot Service**
   ```bash
   # Switch to bot configuration
   cp fly.bot.toml fly.toml
   flyctl launch --name market-sim-bot
   flyctl deploy
   
   # Set bot-specific secrets
   flyctl secrets set TOKEN=your_discord_token
   flyctl secrets set BOT_COMMAND=daily_update
   
   # Restore web configuration
   git checkout fly.toml
   ```

4. **Post-deployment Verification**
   ```bash
   # Check application status
   flyctl status -a market-sim-web
   flyctl status -a market-sim-bot
   
   # Monitor logs
   flyctl logs -a market-sim-web
   flyctl logs -a market-sim-bot
   ```

### Automated Deployment with Scripts

```bash
# Use fly_manager.py for automated operations
python fly_manager.py start    # Start both services
python fly_manager.py stop     # Stop both services
python fly_manager.py status   # Check status
python fly_manager.py logs     # View logs
```

## 🔧 Maintenance Processes

### Daily Operations

1. **Automated Daily Updates**
   - Portfolio value calculations
   - Historical data snapshots
   - Cache maintenance
   - Performance monitoring

2. **Manual Administration**
   ```bash
   # Discord commands (admin only)
   !daily_update     # Force portfolio update
   !flushcache      # Persist cache to database
   !clearcache      # Clear in-memory cache
   !reloadcache     # Reload cache from database
   ```

### Weekly Maintenance

1. **Database Maintenance**
   ```bash
   # Check database integrity
   python fix_database_schema.py --check-only
   
   # Backup database
   cp trading_game.db trading_game_backup_YYYY-MM-DD.db
   ```

2. **Performance Monitoring**
   - Review API usage statistics
   - Monitor cache hit rates
   - Check memory usage patterns
   - Analyze error logs

### Monthly Reviews

1. **Cost Optimization**
   - Review Fly.io usage and costs
   - Optimize cache sizes if needed
   - Update API rate limits
   - Scale resources as needed

2. **Feature Planning**
   - Review user feedback
   - Plan feature enhancements
   - Update documentation
   - Security review

## 🐛 Troubleshooting Processes

### Common Issues and Solutions

1. **Bot Won't Start**
   ```bash
   # Run validation
   python validate_deployment.py
   
   # Common fixes:
   # - Check .env file exists and has correct keys
   # - Verify Discord token validity
   # - Ensure bot permissions in Discord server
   # - Confirm Python version (3.11+ required)
   ```

2. **API Errors**
   ```bash
   # Rate limit exceeded
   # - Wait 1 minute before retrying
   # - Check API key quotas
   # - Consider upgrading API plan
   
   # Invalid symbol errors
   # - Verify stock ticker exists
   # - Check for typos in symbol
   # - Ensure market is open for real-time data
   ```

3. **Database Issues**
   ```bash
   # Corrupted database
   python fix_database_schema.py
   
   # Reset database (WARNING: Deletes all data!)
   rm trading_game.db
   python start_bot.py  # Creates fresh database
   ```

4. **Dashboard Loading Issues**
   ```bash
   # Check port availability
   netstat -ano | findstr :8080
   
   # Verify database permissions
   ls -la trading_game.db
   
   # Check API key configuration
   python -c "import os; print(os.getenv('FINNHUB_API_KEY'))"
   ```

### Error Monitoring

1. **Log Analysis**
   ```bash
   # Local logs
   tail -f logs/market_sim.log
   
   # Fly.io logs
   flyctl logs -a market-sim-web
   flyctl logs -a market-sim-bot
   ```

2. **Performance Metrics**
   - Response times for commands
   - API call success rates
   - Cache hit ratios
   - Memory usage patterns

## 📊 Performance Optimization

### Memory Management

1. **Cache Optimization**
   - Monitor cache sizes
   - Implement LRU eviction
   - Adjust TTL values based on usage
   - Database persistence for durability

2. **Database Optimization**
   - Regular VACUUM operations
   - Index optimization for queries
   - Connection pooling
   - Prepared statement usage

### Cost Optimization (Fly.io)

1. **Resource Management**
   ```bash
   # Scale to zero when not in use
   flyctl scale count 0 -a market-sim-web
   flyctl scale count 0 -a market-sim-bot
   
   # Auto-scale configuration
   min_machines_running = 0
   auto_stop_machines = "stop"
   ```

2. **Monitoring Usage**
   - Track CPU and memory usage
   - Monitor network bandwidth
   - Review storage usage
   - Optimize Docker image sizes

## 🔐 Security Processes

### Environment Security

1. **Secret Management**
   - Never commit .env files
   - Use Fly.io secrets for production
   - Rotate API keys periodically
   - Monitor for exposed credentials

2. **Access Control**
   - Admin commands require Discord permissions
   - Database file permissions
   - API key scope limitations
   - Network security (HTTPS only)

### Data Protection

1. **User Data**
   - Discord IDs only (no personal info)
   - Virtual trading only (no real money)
   - Data encryption in transit
   - Regular backup procedures

2. **API Security**
   - Rate limiting implementation
   - Input validation and sanitization
   - Error message sanitization
   - API key rotation procedures

## 📚 Documentation Maintenance

### Documentation Update Process

1. **Code Changes**
   - Update docstrings for new functions
   - Modify README for new features
   - Update .env.example for new variables
   - Revise deployment guides as needed

2. **Version Control**
   - Tag releases with semantic versioning
   - Maintain CHANGELOG.md
   - Document breaking changes
   - Archive old documentation versions

### Quality Assurance

1. **Code Quality**
   ```bash
   # Run type checking
   python -m mypy *.py
   
   # Check PEP 8 compliance
   python -m flake8 *.py
   
   # Run tests
   python -m pytest tests/
   ```

2. **Documentation Review**
   - Accuracy of instructions
   - Completeness of examples
   - Clarity of explanations
   - Up-to-date screenshots

## 🎯 Success Metrics

### Key Performance Indicators

1. **Technical Metrics**
   - Uptime percentage
   - Response time averages
   - Error rate percentages
   - API quota utilization

2. **User Experience Metrics**
   - Command success rates
   - Dashboard load times
   - User engagement levels
   - Feature adoption rates

3. **Cost Metrics**
   - Monthly hosting costs
   - API usage costs
   - Resource utilization efficiency
   - Cost per active user

---

This documentation should be reviewed and updated regularly to reflect changes in the system, deployment processes, and best practices. For specific technical details, refer to the individual module documentation and inline code comments.
