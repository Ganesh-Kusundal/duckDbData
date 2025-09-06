#!/usr/bin/env python3
"""
Startup script for DuckDB Financial Data API Server
"""

import sys
import os
import argparse
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description="Start DuckDB Financial Data API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--db-path", default="data/financial_data.duckdb", help="Path to DuckDB database file")
    parser.add_argument("--data-root", default="/Users/apple/Downloads/duckDbData/data", help="Root directory for parquet files")
    
    args = parser.parse_args()
    
    # Set environment variables for the application
    os.environ["DUCKDB_PATH"] = args.db_path
    os.environ["DATA_ROOT"] = args.data_root
    
    print(f"🚀 Starting DuckDB Financial Data API Server")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Database: {args.db_path}")
    print(f"   Data Root: {args.data_root}")
    print(f"   Workers: {args.workers}")
    print(f"   Reload: {args.reload}")
    print()
    print(f"📊 API will be available at: http://{args.host}:{args.port}")
    print(f"📚 Interactive docs at: http://{args.host}:{args.port}/docs")
    print(f"🔧 Health check at: http://{args.host}:{args.port}/health")
    print()
    
    try:
        import uvicorn
        from core.duckdb_infra.api_server import app
        
        uvicorn.run(
            "core.duckdb_infra.api_server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level="info"
        )
    except ImportError:
        print("❌ Error: uvicorn not installed. Please install it with:")
        print("   conda install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
