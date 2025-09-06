#!/bin/bash

# Trading Strategy Dashboard Launcher
# This script sets up and runs the Streamlit dashboard

echo "🚀 Starting Trading Strategy Dashboard..."
echo "========================================"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the ui_report directory."
    exit 1
fi

# Check if required files exist
echo "📊 Checking data files..."
if [ ! -f "../fast_backtest_trades_2025.csv" ]; then
    echo "⚠️  Warning: fast_backtest_trades_2025.csv not found"
fi

if [ ! -f "../fast_backtest_pnl_2025.csv" ]; then
    echo "⚠️  Warning: fast_backtest_pnl_2025.csv not found"
fi

if [ ! -f "../optimal_parameters_simple.json" ]; then
    echo "⚠️  Warning: optimal_parameters_simple.json not found"
fi

echo ""
echo "🌐 Starting Streamlit server..."
echo "========================================"
echo "📱 Dashboard will be available at: http://localhost:8501"
echo "🔄 Press Ctrl+C to stop the server"
echo ""

# Start Streamlit
streamlit run app.py --server.headless true --server.address 0.0.0.0
