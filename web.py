#!/usr/bin/env python3
"""
Web Dashboard entry point for DuckDB Financial Infrastructure.
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    from interfaces.api.app import start_server
    start_server()
