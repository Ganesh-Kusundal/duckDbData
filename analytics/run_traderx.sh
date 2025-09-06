#!/bin/bash

# TraderX Dashboard Launcher
# Runs TraderX analytics dashboard in duckdb_infra conda environment

echo "🚀 Starting TraderX — 500-Stock Descriptive Analytics Dashboard"
echo "📊 Environment: duckdb_infra"
echo "🌐 URL: http://localhost:8501"
echo ""

# Set PYTHONPATH to include parent directory for analytics module
export PYTHONPATH="/Users/apple/Downloads/duckDbData:$PYTHONPATH"

# Kill any existing Streamlit processes
echo "🧹 Cleaning up existing processes..."
pkill -f streamlit 2>/dev/null || true
sleep 2

# Run TraderX dashboard
echo "🎯 Launching TraderX dashboard..."
conda run -n duckdb_infra streamlit run dashboard/app.py --server.headless true --server.port 8501

echo ""
echo "✅ TraderX dashboard stopped"
