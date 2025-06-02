# Enhanced Trading Game Dashboard - Robinhood Style
from flask import Flask, render_template_string, url_for, redirect, jsonify
import sqlite3
import requests
from datetime import datetime, date
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
DB_NAME = "trading_game.db"
APP_NAME = "Trading Dashboard"

app = Flask(__name__)

# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────
def get_price(symbol: str) -> float | None:
    """Return live price from Finnhub or None on failure."""
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("c") or None
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return None

def get_company_name(symbol: str) -> str | None:
    """Return company name from Finnhub or None on failure."""
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("name", None)
    except Exception as e:
        print(f"Error fetching company name for {symbol}: {e}")
    return None

def fetch_leaderboard():
    """Return sorted leaderboard list and summary statistics."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT user_id, cash, initial_value, username FROM users")
    users = cursor.fetchall()
    
    leaderboard = []
    total_aum = 0
    total_roi = 0
    valid_users = 0
    
    for user_id, cash, initial_value, username in users:
        name = username if username else f"User-{user_id[-4:]}"
        
        # Get holdings
        cursor.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,))
        holdings = cursor.fetchall()
        
        # Calculate portfolio value
        holdings_value = 0
        total_holdings = len(holdings)
        
        for symbol, shares, avg_price in holdings:
            price = get_price(symbol)
            if price:
                holdings_value += price * shares
        
        total_value = cash + holdings_value
        roi = ((total_value - initial_value) / initial_value) * 100 if initial_value else 0
        pnl = total_value - initial_value
        
        leaderboard.append({
            "user_id": user_id,
            "name": name,
            "cash": cash,
            "holdings_value": holdings_value,
            "total_value": total_value,
            "roi": roi,
            "pnl": pnl,
            "total_holdings": total_holdings
        })
        
        total_aum += total_value
        if initial_value > 0:
            total_roi += roi
            valid_users += 1
    
    # Sort by total value descending
    leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
    
    # Calculate summary stats
    avg_roi = total_roi / valid_users if valid_users > 0 else 0
    best_performer = leaderboard[0]["name"] if leaderboard else "N/A"
    
    summary = {
        "total_users": len(users),
        "total_aum": total_aum,
        "avg_roi": avg_roi,
        "best_performer": best_performer
    }
    
    conn.close()
    return leaderboard, summary

def fetch_user_portfolio(user_id: str):
    """Return detailed portfolio data for a specific user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get user data
    cursor.execute("SELECT username, cash, initial_value FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        return None
    
    username, cash, initial_value = user_row
    name = username if username else f"User-{user_id[-4:]}"
    
    # Get holdings
    cursor.execute("SELECT symbol, shares, avg_price FROM holdings WHERE user_id = ?", (user_id,))
    holdings_rows = cursor.fetchall()
    
    holdings = []
    holdings_value = 0
    
    for symbol, shares, avg_price in holdings_rows:
        price = get_price(symbol)
        if not price:
            # Use avg_price as fallback if live price fails
            price = avg_price
            
        value = price * shares
        change = ((price - avg_price) / avg_price) * 100 if avg_price else 0
        unrealized_pnl = (price - avg_price) * shares
        holdings_value += value
        
        # Get company name
        company_name = get_company_name(symbol)
        
        holdings.append({
            "symbol": symbol,
            "company_name": company_name or symbol,
            "shares": shares,
            "avg_price": avg_price,
            "price": price,
            "value": value,
            "change": change,
            "unrealized_pnl": unrealized_pnl,
            "portfolio_percent": 0  # Will calculate after we know total
        })
    
    # Calculate total value and portfolio percentages
    total_value = cash + holdings_value
    for holding in holdings:
        holding["portfolio_percent"] = (holding["value"] / total_value) * 100 if total_value > 0 else 0
    
    # Sort holdings by value descending
    holdings.sort(key=lambda h: h["value"], reverse=True)
    
    # Get historical data
    cursor.execute("SELECT date, portfolio_value FROM history WHERE user_id = ? ORDER BY date", (user_id,))
    history_rows = cursor.fetchall()
    
    history_dates = [row[0] for row in history_rows]
    history_values = [row[1] for row in history_rows]
    
    # Prepare pie chart data (include cash as a slice if > 0)
    pie_labels = [h["symbol"] for h in holdings]
    pie_values = [h["value"] for h in holdings]
    
    if cash > 0:
        pie_labels.append("Cash")
        pie_values.append(cash)
    
    roi = ((total_value - initial_value) / initial_value) * 100 if initial_value else 0
    
    conn.close()
    
    return {
        "name": name,
        "cash": cash,
        "holdings_value": holdings_value,
        "total_value": total_value,
        "roi": roi,
        "holdings": holdings,
        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "history_dates": history_dates,
        "history_values": history_values
    }

# ──────────────────────────────────────────────────────────────
# HTML Templates - Robinhood Style
# ──────────────────────────────────────────────────────────────
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Robinhood-Inspired Dark Theme */
        :root {
            --rh-black: #0B0E11;
            --rh-dark: #1A1E23;
            --rh-medium: #242932;
            --rh-light: #2F343D;
            --rh-border: #3A404A;
            --rh-white: #FFFFFF;
            --rh-text-primary: #FFFFFF;
            --rh-text-secondary: #9CA0A6;
            --rh-text-muted: #6B7280;
            --rh-green: #00C805;
            --rh-red: #FF5A52;
            --rh-blue: #5AC53B;
            --rh-purple: #8B5CF6;
            --rh-yellow: #F7931E;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--rh-black);
            color: var(--rh-text-primary);
            font-size: 14px;
            line-height: 1.5;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* Navigation */
        .navbar {
            background: var(--rh-dark);
            border-bottom: 1px solid var(--rh-border);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
        }
        
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .nav-brand {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--rh-white);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .nav-brand:hover {
            color: var(--rh-blue);
        }
        
        .nav-actions {
            display: flex;
            gap: 0.75rem;
        }
        
        /* Buttons */
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            border: 1px solid transparent;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn-primary {
            background: var(--rh-blue);
            color: var(--rh-black);
            border-color: var(--rh-blue);
        }
        
        .btn-primary:hover {
            background: #4AB02A;
            transform: translateY(-1px);
        }
        
        .btn-outline {
            background: transparent;
            color: var(--rh-text-secondary);
            border-color: var(--rh-border);
        }
        
        .btn-outline:hover {
            background: var(--rh-medium);
            color: var(--rh-white);
            border-color: var(--rh-light);
        }
        
        /* Container */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }
        
        /* Grid */
        .grid {
            display: grid;
            gap: 1.5rem;
        }
        
        .grid-4 {
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }
        
        .grid-2 {
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        }
        
        /* Cards */
        .card {
            background: var(--rh-dark);
            border: 1px solid var(--rh-border);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        
        .card:hover {
            border-color: var(--rh-light);
            transform: translateY(-2px);
        }
        
        .card-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--rh-border);
            background: var(--rh-medium);
        }
        
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--rh-white);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .card-body {
            padding: 1.5rem;
        }
        
        /* Metric Cards */
        .metric-card {
            text-align: center;
            background: var(--rh-dark);
            border: 1px solid var(--rh-border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
        }
        
        .metric-card:hover {
            border-color: var(--rh-light);
            transform: translateY(-2px);
        }
        
        .metric-icon {
            font-size: 2rem;
            margin-bottom: 0.75rem;
            opacity: 0.8;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 500;
            color: var(--rh-text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0;
        }
        
        /* Table */
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--rh-border);
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            background: var(--rh-dark);
        }
        
        .table th {
            background: var(--rh-medium);
            color: var(--rh-text-secondary);
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 1rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--rh-border);
        }
        
        .table td {
            padding: 1rem 0.75rem;
            border-bottom: 1px solid var(--rh-border);
            vertical-align: middle;
        }
        
        .table tr:hover {
            background: var(--rh-medium);
        }
        
        .table tr:last-child td {
            border-bottom: none;
        }
        
        /* Colors */
        .text-green {
            color: var(--rh-green);
            font-weight: 600;
        }
        
        .text-red {
            color: var(--rh-red);
            font-weight: 600;
        }
        
        .text-blue {
            color: var(--rh-blue);
        }
        
        .text-yellow {
            color: var(--rh-yellow);
        }
        
        .text-purple {
            color: var(--rh-purple);
        }
        
        .text-secondary {
            color: var(--rh-text-secondary);
        }
        
        .text-muted {
            color: var(--rh-text-muted);
            font-size: 13px;
        }
        
        /* Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-gold {
            background: linear-gradient(135deg, var(--rh-yellow), #E67E22);
            color: var(--rh-black);
        }
        
        .badge-silver {
            background: var(--rh-text-secondary);
            color: var(--rh-black);
        }
        
        /* Charts */
        .chart-container {
            position: relative;
            height: 300px;
            background: var(--rh-medium);
            border-radius: 8px;
            padding: 1rem;
        }
        
        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            color: var(--rh-text-secondary);
            font-size: 14px;
        }
        
        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid var(--rh-border);
            border-top: 2px solid var(--rh-blue);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .metric-card {
                padding: 1rem;
            }
            
            .metric-value {
                font-size: 1.5rem;
            }
            
            .table th,
            .table td {
                padding: 0.75rem 0.5rem;
                font-size: 13px;
            }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="nav-container">
            <a href="/" class="nav-brand">
                <i class="fas fa-chart-line"></i>
                {{ app_name }}
            </a>
            <div class="nav-actions">
                <button class="btn btn-primary" onclick="refreshData()">
                    <i class="fas fa-sync-alt"></i>
                    Refresh
                </button>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Market Summary -->
        <div class="grid grid-4" style="margin-bottom: 2rem;">
            <div class="metric-card">
                <div class="metric-icon text-blue">
                    <i class="fas fa-users"></i>
                </div>
                <div class="metric-label">Active Traders</div>
                <div class="metric-value text-blue">{{ summary.total_users }}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-green">
                    <i class="fas fa-dollar-sign"></i>
                </div>
                <div class="metric-label">Total AUM</div>
                <div class="metric-value text-green">${{ "{:,.0f}".format(summary.total_aum) }}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-yellow">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="metric-label">Avg ROI</div>
                <div class="metric-value {% if summary.avg_roi >= 0 %}text-green{% else %}text-red{% endif %}">
                    {{ "{:+.1f}".format(summary.avg_roi) }}%
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-purple">
                    <i class="fas fa-trophy"></i>
                </div>
                <div class="metric-label">Best Performer</div>
                <div class="metric-value text-purple">{{ summary.best_performer }}</div>
            </div>
        </div>

        <!-- Leaderboard -->
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-trophy text-yellow"></i>
                    Leaderboard
                </h2>
            </div>
            <div class="card-body" style="padding: 0;">
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th><i class="fas fa-medal"></i> Rank</th>
                                <th><i class="fas fa-user"></i> Trader</th>
                                <th><i class="fas fa-wallet"></i> Cash</th>
                                <th><i class="fas fa-chart-pie"></i> Holdings</th>
                                <th><i class="fas fa-money-bill"></i> Total Value</th>
                                <th><i class="fas fa-percentage"></i> ROI</th>
                                <th><i class="fas fa-chart-line"></i> P&L</th>
                                <th><i class="fas fa-eye"></i> Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for user in leaderboard %}
                            <tr>
                                <td>
                                    {% if loop.index == 1 %}
                                        <span class="badge badge-gold">
                                            <i class="fas fa-crown"></i> {{ loop.index }}
                                        </span>
                                    {% elif loop.index <= 3 %}
                                        <span class="badge badge-silver">{{ loop.index }}</span>
                                    {% else %}
                                        <span style="font-weight: 600;">{{ loop.index }}</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <div>
                                        <div style="font-weight: 600;">{{ user.name }}</div>
                                        {% if user.total_holdings > 0 %}
                                            <div class="text-muted">{{ user.total_holdings }} positions</div>
                                        {% endif %}
                                    </div>
                                </td>
                                <td>${{ "{:,.0f}".format(user.cash) }}</td>
                                <td>${{ "{:,.0f}".format(user.holdings_value) }}</td>
                                <td style="font-weight: 700;">${{ "{:,.0f}".format(user.total_value) }}</td>
                                <td class="{% if user.roi >= 0 %}text-green{% else %}text-red{% endif %}">
                                    {{ "{:+.1f}".format(user.roi) }}%
                                </td>
                                <td class="{% if user.pnl >= 0 %}text-green{% else %}text-red{% endif %}">
                                    ${{ "{:+,.0f}".format(user.pnl) }}
                                </td>
                                <td>
                                    <a href="/user/{{ user.user_id }}" class="btn btn-outline">
                                        <i class="fas fa-chart-area"></i>
                                        View Portfolio
                                    </a>
                                </td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        function refreshData() {
            const spinner = document.querySelector('.spinner');
            if (spinner) return; // Already refreshing
            
            const refreshBtn = document.querySelector('.btn-primary');
            const originalContent = refreshBtn.innerHTML;
            
            refreshBtn.innerHTML = '<div class="spinner"></div> Refreshing...';
            refreshBtn.disabled = true;
            
            setTimeout(() => {
                location.reload();
            }, 1000);
        }
    </script>
</body>
</html>
"""

USER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ user.name }} - Portfolio | {{ app_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Same styles as INDEX_HTML for consistency */
        :root {
            --rh-black: #0B0E11;
            --rh-dark: #1A1E23;
            --rh-medium: #242932;
            --rh-light: #2F343D;
            --rh-border: #3A404A;
            --rh-white: #FFFFFF;
            --rh-text-primary: #FFFFFF;
            --rh-text-secondary: #9CA0A6;
            --rh-text-muted: #6B7280;
            --rh-green: #00C805;
            --rh-red: #FF5A52;
            --rh-blue: #5AC53B;
            --rh-purple: #8B5CF6;
            --rh-yellow: #F7931E;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--rh-black);
            color: var(--rh-text-primary);
            font-size: 14px;
            line-height: 1.5;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .navbar {
            background: var(--rh-dark);
            border-bottom: 1px solid var(--rh-border);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .nav-brand {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--rh-white);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            border: 1px solid transparent;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn-outline {
            background: transparent;
            color: var(--rh-text-secondary);
            border-color: var(--rh-border);
        }
        
        .btn-outline:hover {
            background: var(--rh-medium);
            color: var(--rh-white);
            border-color: var(--rh-light);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }
        
        .grid {
            display: grid;
            gap: 1.5rem;
        }
        
        .grid-4 {
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }
        
        .grid-2 {
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        }
        
        .card {
            background: var(--rh-dark);
            border: 1px solid var(--rh-border);
            border-radius: 12px;
            overflow: hidden;
        }
        
        .card-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--rh-border);
            background: var(--rh-medium);
        }
        
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--rh-white);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .card-body {
            padding: 1.5rem;
        }
        
        .metric-card {
            text-align: center;
            background: var(--rh-dark);
            border: 1px solid var(--rh-border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
        }
        
        .metric-card:hover {
            border-color: var(--rh-light);
            transform: translateY(-2px);
        }
        
        .metric-icon {
            font-size: 2rem;
            margin-bottom: 0.75rem;
            opacity: 0.8;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 500;
            color: var(--rh-text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0;
        }
        
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--rh-border);
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            background: var(--rh-dark);
        }
        
        .table th {
            background: var(--rh-medium);
            color: var(--rh-text-secondary);
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 1rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--rh-border);
        }
        
        .table td {
            padding: 1rem 0.75rem;
            border-bottom: 1px solid var(--rh-border);
            vertical-align: middle;
        }
        
        .table tr:hover {
            background: var(--rh-medium);
        }
        
        .text-green {
            color: var(--rh-green);
            font-weight: 600;
        }
        
        .text-red {
            color: var(--rh-red);
            font-weight: 600;
        }
        
        .text-blue {
            color: var(--rh-blue);
        }
        
        .text-yellow {
            color: var(--rh-yellow);
        }
        
        .text-purple {
            color: var(--rh-purple);
        }
        
        .text-muted {
            color: var(--rh-text-muted);
            font-size: 13px;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            background: var(--rh-medium);
            border-radius: 8px;
            padding: 1rem;
        }
        
        .page-title {
            text-align: center;
            margin-bottom: 2rem;
            color: var(--rh-white);
            font-size: 1.75rem;
            font-weight: 700;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .metric-card {
                padding: 1rem;
            }
            
            .metric-value {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="nav-container">
            <a href="/" class="nav-brand">
                <i class="fas fa-chart-line"></i>
                {{ app_name }}
            </a>
            <div class="nav-actions">
                <a href="/" class="btn btn-outline">
                    <i class="fas fa-arrow-left"></i>
                    Back to Leaderboard
                </a>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- User Header -->
        <h1 class="page-title">
            <i class="fas fa-user-circle"></i>
            {{ user.name }}'s Portfolio
        </h1>

        <!-- Portfolio Summary Cards -->
        <div class="grid grid-4" style="margin-bottom: 2rem;">
            <div class="metric-card">
                <div class="metric-icon text-green">
                    <i class="fas fa-wallet"></i>
                </div>
                <div class="metric-label">Cash</div>
                <div class="metric-value text-green">${{ "{:,.0f}".format(user.cash) }}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-blue">
                    <i class="fas fa-chart-pie"></i>
                </div>
                <div class="metric-label">Holdings Value</div>
                <div class="metric-value text-blue">${{ "{:,.0f}".format(user.holdings_value) }}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-purple">
                    <i class="fas fa-money-bill"></i>
                </div>
                <div class="metric-label">Total Value</div>
                <div class="metric-value text-purple">${{ "{:,.0f}".format(user.total_value) }}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon text-yellow">
                    <i class="fas fa-percentage"></i>
                </div>
                <div class="metric-label">ROI</div>
                <div class="metric-value {% if user.roi >= 0 %}text-green{% else %}text-red{% endif %}">
                    {{ "{:+.1f}".format(user.roi) }}%
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-2" style="margin-bottom: 2rem;">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">
                        <i class="fas fa-chart-pie"></i>
                        Portfolio Allocation
                    </h3>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="pieChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">
                        <i class="fas fa-chart-line"></i>
                        Performance Over Time
                    </h3>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="lineChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Holdings Table -->
        {% if user.holdings %}
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="fas fa-list"></i>
                    Holdings Details
                </h3>
            </div>
            <div class="card-body" style="padding: 0;">
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th><i class="fas fa-tag"></i> Stock</th>
                                <th><i class="fas fa-layer-group"></i> Shares</th>
                                <th><i class="fas fa-dollar-sign"></i> Avg Cost</th>
                                <th><i class="fas fa-chart-line"></i> Current Price</th>
                                <th><i class="fas fa-money-bill"></i> Position Value</th>
                                <th><i class="fas fa-percentage"></i> Price Change</th>
                                <th><i class="fas fa-calculator"></i> Unrealized P&L</th>
                                <th><i class="fas fa-chart-pie"></i> % of Portfolio</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for h in user.holdings %}
                            <tr>
                                <td>
                                    <div>
                                        <div style="font-weight: 600;">{{ h.symbol }}</div>
                                        <div class="text-muted">{{ h.company_name }}</div>
                                    </div>
                                </td>
                                <td>{{ "{:,.0f}".format(h.shares) }}</td>
                                <td>${{ "{:.2f}".format(h.avg_price) }}</td>
                                <td>${{ "{:.2f}".format(h.price) }}</td>
                                <td style="font-weight: 700;">${{ "{:,.0f}".format(h.value) }}</td>
                                <td class="{% if h.change >= 0 %}text-green{% else %}text-red{% endif %}">
                                    {{ "{:+.1f}".format(h.change) }}%
                                </td>
                                <td class="{% if h.unrealized_pnl >= 0 %}text-green{% else %}text-red{% endif %}">
                                    ${{ "{:+,.0f}".format(h.unrealized_pnl) }}
                                </td>
                                <td>{{ "{:.1f}".format(h.portfolio_percent) }}%</td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% else %}
        <div class="card">
            <div class="card-body" style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; color: var(--rh-text-muted); margin-bottom: 1rem;">
                    <i class="fas fa-chart-pie"></i>
                </div>
                <h3 style="color: var(--rh-text-secondary); margin-bottom: 0.5rem;">No Holdings Yet</h3>
                <p class="text-muted">This portfolio consists entirely of cash.</p>
            </div>
        </div>
        {% endif %}
    </div>

    <script>
        // Chart.js configuration for consistent dark theme
        Chart.defaults.color = '#9CA0A6';
        Chart.defaults.borderColor = '#3A404A';
        Chart.defaults.backgroundColor = '#242932';

        // Pie Chart for Portfolio Allocation
        {% if user.pie_labels|length > 0 %}
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: {{ user.pie_labels|tojson }},
                datasets: [{
                    data: {{ user.pie_values|tojson }},
                    backgroundColor: [
                        '#00C805', '#FF5A52', '#5AC53B', '#8B5CF6', 
                        '#F7931E', '#06B6D4', '#EF4444', '#10B981',
                        '#F59E0B', '#8B5CF6'
                    ],
                    borderWidth: 2,
                    borderColor: '#1A1E23'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'right',
                        labels: { 
                            color: '#9CA0A6',
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                }
            }
        });
        {% endif %}

        // Line Chart for Historical Performance
        {% if user.history_dates|length > 0 %}
        const lineCtx = document.getElementById('lineChart').getContext('2d');
        new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: {{ user.history_dates|tojson }},
                datasets: [{
                    label: 'Portfolio Value',
                    data: {{ user.history_values|tojson }},
                    borderColor: '#5AC53B',
                    backgroundColor: 'rgba(90, 197, 59, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#5AC53B',
                    pointBorderColor: '#1A1E23',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            color: '#9CA0A6',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: { color: '#3A404A' }
                    },
                    x: {
                        ticks: { color: '#9CA0A6' },
                        grid: { color: '#3A404A' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        {% endif %}
    </script>
</body>
</html>
"""

# ──────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    leaderboard, summary = fetch_leaderboard()
    return render_template_string(
        INDEX_HTML, 
        leaderboard=leaderboard, 
        summary=summary,
        app_name=APP_NAME
    )

@app.route("/user/<user_id>")
def user_detail(user_id):
    user_data = fetch_user_portfolio(user_id)
    if not user_data:
        return redirect(url_for("index"))

    return render_template_string(
        USER_HTML,
        user=user_data,
        app_name=APP_NAME
    )

@app.route("/api/refresh")
def api_refresh():
    """API endpoint to refresh data without full page reload."""
    leaderboard, summary = fetch_leaderboard()
    return jsonify({"leaderboard": leaderboard, "summary": summary})

# ──────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Starting {APP_NAME}")
    port = int(os.getenv("PORT", 5001))  # Use Railway's PORT or default to 5001
    print(f"📊 Dashboard will be available at: http://localhost:{port}")
    print("🎨 Now featuring Robinhood-style design!")
    app.run(debug=False, host="0.0.0.0", port=port)
