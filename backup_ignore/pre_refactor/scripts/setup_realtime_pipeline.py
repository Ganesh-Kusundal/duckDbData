#!/usr/bin/env python3
"""
Real-Time Pipeline Setup Script
==============================

One-time setup script to prepare the real-time data pipeline system.
Checks dependencies, creates directories, and validates configuration.

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
from pathlib import Path
import logging
import subprocess
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Check Python version compatibility"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    
    logger.info(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_conda_environment():
    """Check if running in correct conda environment"""
    conda_env = os.getenv('CONDA_DEFAULT_ENV')
    if conda_env != 'duckdb_infra':
        logger.warning(f"⚠️  Not in 'duckdb_infra' environment (current: {conda_env})")
        logger.info("Run: conda activate duckdb_infra")
        return False
    
    logger.info(f"✅ Conda environment: {conda_env}")
    return True

def check_required_packages():
    """Check if required packages are installed"""
    required_packages = [
        'pandas',
        'numpy',
        'duckdb',
        'fastapi',
        'uvicorn',
        'requests',
        'schedule',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"❌ {package}")
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.info(f"Install with: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_dhan_api():
    """Check Dhan API integration"""
    try:
        from Dhan_Tradehull import Tradehull
        logger.info("✅ Dhan API package available")
        
        # Check credentials
        client_id = os.getenv('DHAN_CLIENT_ID')
        access_token = os.getenv('DHAN_API_TOKEN')
        
        if not client_id or not access_token:
            logger.warning("⚠️  Dhan API credentials not found in environment")
            logger.info("Set environment variables:")
            logger.info("  export DHAN_CLIENT_ID='your_client_id'")
            logger.info("  export DHAN_API_TOKEN='your_api_token'")
            return False
        
        logger.info("✅ Dhan API credentials found")
        return True
        
    except ImportError:
        logger.error("❌ Dhan API package not found")
        logger.info("Install with: pip install Dhan_Tradehull")
        return False

def create_directories():
    """Create required directories"""
    directories = [
        'logs',
        'data/technical_indicators',
        'config',
        'backups'
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Directory: {directory}")
    
    return True

def check_database_connection():
    """Check database connectivity"""
    try:
        sys.path.append(str(Path(__file__).parent))
        from core.duckdb_infra.database import DuckDBManager
        
        db = DuckDBManager()
        symbols = db.get_available_symbols()
        
        if symbols:
            logger.info(f"✅ Database connection: {len(symbols)} symbols available")
            return True
        else:
            logger.warning("⚠️  Database connected but no symbols found")
            logger.info("Load data first with existing scripts")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_technical_indicators():
    """Check technical indicators system"""
    try:
        from core.technical_indicators.calculator import TechnicalIndicatorsCalculator
        from core.technical_indicators.storage import TechnicalIndicatorsStorage
        
        calculator = TechnicalIndicatorsCalculator()
        storage = TechnicalIndicatorsStorage('data/technical_indicators')
        
        logger.info(f"✅ Technical indicators system available")
        logger.info(f"   Using TA-Lib: {calculator.use_talib}")
        logger.info(f"   Using pandas_ta: {calculator.use_ta}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Technical indicators system error: {e}")
        return False

def create_sample_env_file():
    """Create sample .env file"""
    env_file = Path('config/.env.sample')
    
    env_content = """# Dhan API Configuration
DHAN_CLIENT_ID=your_client_id_here
DHAN_API_TOKEN=your_api_token_here

# Email Alert Configuration (Optional)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL_RECIPIENTS=admin@company.com,trader@company.com

# Slack Alert Configuration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Database Configuration
DATABASE_PATH=data/financial_data.duckdb

# Logging Configuration
LOG_LEVEL=INFO
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    logger.info(f"✅ Sample environment file created: {env_file}")
    logger.info("   Copy to config/.env and update with your credentials")
    
    return True

def validate_configuration():
    """Validate configuration files"""
    config_file = Path('config/realtime_config.json')
    
    if not config_file.exists():
        logger.warning(f"⚠️  Configuration file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required sections
        required_sections = ['pipeline', 'scheduler', 'monitoring']
        for section in required_sections:
            if section not in config:
                logger.error(f"❌ Missing configuration section: {section}")
                return False
        
        logger.info("✅ Configuration file valid")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False

def run_basic_test():
    """Run basic functionality test"""
    try:
        logger.info("🧪 Running basic functionality test...")
        
        # Test data pipeline components
        from scripts.realtime_data_pipeline import PipelineConfig
        config = PipelineConfig()
        logger.info("✅ Pipeline configuration loaded")
        
        # Test scheduler components
        from scripts.pipeline_scheduler import SchedulerConfig
        scheduler_config = SchedulerConfig()
        logger.info("✅ Scheduler configuration loaded")
        
        # Test monitor components
        from scripts.pipeline_monitor import AlertConfig
        alert_config = AlertConfig()
        logger.info("✅ Monitor configuration loaded")
        
        logger.info("✅ All components test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic test failed: {e}")
        return False

def print_next_steps():
    """Print next steps for user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 NEXT STEPS:")
    print("\n1. Configure API Credentials:")
    print("   • Copy config/.env.sample to config/.env")
    print("   • Update with your Dhan API credentials")
    print("\n2. Start the Real-Time System:")
    print("   python scripts/start_realtime_system.py")
    print("\n3. Check System Status:")
    print("   python scripts/start_realtime_system.py --status")
    print("   curl http://localhost:8001/status")
    print("\n4. Monitor the System:")
    print("   • Logs: tail -f logs/realtime_pipeline.log")
    print("   • API: http://localhost:8001")
    print("   • Health: http://localhost:8001/health")
    print("\n5. Stop the System:")
    print("   python scripts/start_realtime_system.py --stop")
    print("\n📚 Documentation:")
    print("   • User Guide: REALTIME_PIPELINE_GUIDE.md")
    print("   • Technical Indicators: TECHNICAL_INDICATORS_USER_GUIDE.md")
    print("   • Quick Reference: QUICK_REFERENCE.md")
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🚀 Real-Time Pipeline Setup")
    print("="*60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Conda Environment", check_conda_environment),
        ("Required Packages", check_required_packages),
        ("Dhan API", check_dhan_api),
        ("Directories", create_directories),
        ("Database Connection", check_database_connection),
        ("Technical Indicators", check_technical_indicators),
        ("Sample Environment File", create_sample_env_file),
        ("Configuration", validate_configuration),
        ("Basic Test", run_basic_test)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        try:
            if check_func():
                passed += 1
            else:
                logger.warning(f"⚠️  {name} check failed (not critical)")
        except Exception as e:
            logger.error(f"❌ {name} check error: {e}")
    
    print(f"\n📊 Setup Results: {passed}/{total} checks passed")
    
    if passed >= total - 2:  # Allow 2 non-critical failures
        print("✅ Setup completed successfully!")
        print_next_steps()
        return True
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
