#!/usr/bin/env python3
"""
Command Line Interface entry point for DuckDB Financial Infrastructure.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set up environment
os.environ.setdefault('DUCKDB_FINANCIAL_ENV', 'development')

if __name__ == "__main__":
    try:
        # Import CLI directly to avoid package-level import issues
        from src.interfaces.cli.main import app
        app()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're in the project root directory")
        print("Try running from the project root with: python cli.py")
        sys.exit(1)
