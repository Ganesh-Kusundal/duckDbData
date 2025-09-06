#!/usr/bin/env python3
"""
Analytics Dashboard Runner
==========================

Simple script to run the Streamlit analytics dashboard.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the analytics dashboard."""
    # Get the dashboard directory
    dashboard_dir = Path(__file__).parent / "dashboard"
    app_file = dashboard_dir / "app.py"

    if not app_file.exists():
        print(f"❌ Error: Dashboard app not found at {app_file}")
        sys.exit(1)

    print("🚀 Starting DuckDB Analytics Dashboard...")
    print("📊 URL: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 50)

    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_file), "--server.port", "8501"
        ], cwd=str(dashboard_dir))

    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
