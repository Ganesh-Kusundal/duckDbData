#!/usr/bin/env python3
"""
Pipeline Scheduler Service
=========================

Manages the real-time data pipeline with advanced scheduling, monitoring, and recovery features.
Provides a service-like interface for production deployment.

Features:
- Market hours awareness
- Automatic start/stop based on market schedule
- Health monitoring and recovery
- Configuration management
- REST API for control and monitoring
- Logging and alerting
- Performance metrics

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
import signal
import json
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Any
import threading
import time as time_module
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
import schedule

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.realtime_data_pipeline import RealTimeDataPipeline, PipelineConfig
from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineStatus(BaseModel):
    """Pipeline status model"""
    running: bool
    market_open: bool
    uptime_seconds: float
    last_data_update: Optional[datetime]
    last_indicator_update: Optional[datetime]
    data_updates_count: int
    indicator_updates_count: int
    errors_count: int
    symbols_processed: int
    records_processed: int

class SchedulerConfig(BaseModel):
    """Scheduler configuration model"""
    auto_start_enabled: bool = True
    auto_stop_enabled: bool = True
    health_check_interval: int = 30  # seconds
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: int = 60  # seconds
    api_port: int = 8001
    api_host: str = "0.0.0.0"

@dataclass
class SchedulerStats:
    """Scheduler statistics"""
    start_time: datetime
    pipeline_starts: int = 0
    pipeline_stops: int = 0
    pipeline_restarts: int = 0
    health_checks: int = 0
    api_requests: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)

class PipelineScheduler:
    """Advanced scheduler for the real-time data pipeline"""
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize the scheduler"""
        self.config = config or SchedulerConfig()
        self.stats = SchedulerStats(start_time=datetime.now())
        self.pipeline: Optional[RealTimeDataPipeline] = None
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Restart tracking
        self.restart_attempts = 0
        self.last_restart_time: Optional[datetime] = None
        
        # Health monitoring
        self.last_health_check: Optional[datetime] = None
        self.health_status = "unknown"
        
        # Threading
        self.scheduler_thread: Optional[threading.Thread] = None
        self.health_thread: Optional[threading.Thread] = None
        
        # FastAPI app for control interface
        self.app = self._create_api()
        
        logger.info("Pipeline scheduler initialized")
    
    def _create_api(self) -> FastAPI:
        """Create FastAPI application for control interface"""
        app = FastAPI(
            title="Pipeline Scheduler API",
            description="Control and monitor the real-time data pipeline",
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            """API root endpoint"""
            self.stats.api_requests += 1
            return {
                "service": "Pipeline Scheduler",
                "version": "1.0.0",
                "status": "running" if self.running else "stopped",
                "uptime": (datetime.now() - self.stats.start_time).total_seconds()
            }
        
        @app.get("/status", response_model=Dict[str, Any])
        async def get_status():
            """Get detailed pipeline status"""
            self.stats.api_requests += 1
            
            pipeline_status = None
            if self.pipeline:
                pipeline_status = self.pipeline.get_status()
            
            return {
                "scheduler": {
                    "running": self.running,
                    "health_status": self.health_status,
                    "last_health_check": self.last_health_check,
                    "restart_attempts": self.restart_attempts,
                    "last_restart_time": self.last_restart_time,
                    "stats": self.stats.to_dict()
                },
                "pipeline": pipeline_status,
                "market": {
                    "is_open": self._is_market_open(),
                    "next_open": self._get_next_market_open(),
                    "next_close": self._get_next_market_close()
                }
            }
        
        @app.post("/start")
        async def start_pipeline():
            """Start the pipeline manually"""
            self.stats.api_requests += 1
            
            if self.pipeline and self.pipeline.running:
                raise HTTPException(status_code=400, detail="Pipeline is already running")
            
            success = self._start_pipeline()
            if success:
                return {"message": "Pipeline started successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to start pipeline")
        
        @app.post("/stop")
        async def stop_pipeline():
            """Stop the pipeline manually"""
            self.stats.api_requests += 1
            
            if not self.pipeline or not self.pipeline.running:
                raise HTTPException(status_code=400, detail="Pipeline is not running")
            
            self._stop_pipeline()
            return {"message": "Pipeline stopped successfully"}
        
        @app.post("/restart")
        async def restart_pipeline():
            """Restart the pipeline"""
            self.stats.api_requests += 1
            
            self._restart_pipeline()
            return {"message": "Pipeline restart initiated"}
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            self.stats.api_requests += 1
            
            health_status = self._perform_health_check()
            
            return {
                "status": health_status,
                "timestamp": datetime.now(),
                "pipeline_running": self.pipeline.running if self.pipeline else False,
                "market_open": self._is_market_open()
            }
        
        @app.get("/metrics")
        async def get_metrics():
            """Get performance metrics"""
            self.stats.api_requests += 1
            
            metrics = {
                "scheduler_stats": self.stats.to_dict(),
                "uptime_seconds": (datetime.now() - self.stats.start_time).total_seconds()
            }
            
            if self.pipeline:
                pipeline_status = self.pipeline.get_status()
                metrics["pipeline_stats"] = pipeline_status.get("stats", {})
            
            return metrics
        
        @app.get("/config")
        async def get_config():
            """Get current configuration"""
            self.stats.api_requests += 1
            
            config = {
                "scheduler": self.config.dict(),
            }
            
            if self.pipeline:
                pipeline_status = self.pipeline.get_status()
                config["pipeline"] = pipeline_status.get("config", {})
            
            return config
        
        return app
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now()
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = time(9, 15)
        market_close = time(15, 30)
        current_time = now.time()
        
        return market_open <= current_time <= market_close
    
    def _get_next_market_open(self) -> datetime:
        """Get next market opening time"""
        now = datetime.now()
        
        # If market is currently open, return tomorrow's opening
        if self._is_market_open():
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5:  # Skip weekends
                next_day += timedelta(days=1)
            return next_day.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # If it's before market open today and it's a weekday
        if now.weekday() < 5 and now.time() < time(9, 15):
            return now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # Otherwise, next weekday
        next_day = now + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day.replace(hour=9, minute=15, second=0, microsecond=0)
    
    def _get_next_market_close(self) -> datetime:
        """Get next market closing time"""
        now = datetime.now()
        
        # If market is open today
        if now.weekday() < 5 and now.time() < time(15, 30):
            return now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Next weekday
        next_day = now + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day.replace(hour=15, minute=30, second=0, microsecond=0)
    
    def _start_pipeline(self) -> bool:
        """Start the data pipeline"""
        try:
            if self.pipeline and self.pipeline.running:
                logger.warning("Pipeline is already running")
                return True
            
            logger.info("Starting data pipeline")
            
            # Create new pipeline instance
            pipeline_config = PipelineConfig()
            self.pipeline = RealTimeDataPipeline(pipeline_config)
            
            # Start the pipeline
            self.pipeline.start()
            
            self.stats.pipeline_starts += 1
            self.restart_attempts = 0  # Reset restart attempts on successful start
            
            logger.info("Data pipeline started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}")
            return False
    
    def _stop_pipeline(self):
        """Stop the data pipeline"""
        try:
            if not self.pipeline or not self.pipeline.running:
                logger.warning("Pipeline is not running")
                return
            
            logger.info("Stopping data pipeline")
            self.pipeline.stop()
            self.stats.pipeline_stops += 1
            
            logger.info("Data pipeline stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")
    
    def _restart_pipeline(self):
        """Restart the data pipeline"""
        logger.info("Restarting data pipeline")
        
        self._stop_pipeline()
        time_module.sleep(5)  # Wait a bit before restart
        
        success = self._start_pipeline()
        if success:
            self.stats.pipeline_restarts += 1
            self.last_restart_time = datetime.now()
            logger.info("Pipeline restarted successfully")
        else:
            logger.error("Failed to restart pipeline")
    
    def _perform_health_check(self) -> str:
        """Perform health check on the pipeline"""
        try:
            self.stats.health_checks += 1
            self.last_health_check = datetime.now()
            
            if not self.pipeline:
                self.health_status = "no_pipeline"
                return self.health_status
            
            if not self.pipeline.running:
                self.health_status = "pipeline_stopped"
                return self.health_status
            
            # Check if pipeline is responsive
            status = self.pipeline.get_status()
            
            # Check for recent updates during market hours
            if self._is_market_open():
                last_update = status.get('stats', {}).get('last_data_update')
                if last_update:
                    last_update_time = datetime.fromisoformat(last_update) if isinstance(last_update, str) else last_update
                    time_since_update = (datetime.now() - last_update_time).total_seconds()
                    
                    if time_since_update > 300:  # 5 minutes
                        self.health_status = "stale_data"
                        return self.health_status
            
            # Check error rate
            stats = status.get('stats', {})
            total_operations = stats.get('data_updates', 0) + stats.get('indicator_updates', 0)
            error_rate = stats.get('errors', 0) / max(total_operations, 1)
            
            if error_rate > 0.1:  # More than 10% error rate
                self.health_status = "high_error_rate"
                return self.health_status
            
            self.health_status = "healthy"
            return self.health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health_status = "health_check_failed"
            return self.health_status
    
    def _schedule_market_operations(self):
        """Schedule automatic start/stop based on market hours"""
        if not self.config.auto_start_enabled and not self.config.auto_stop_enabled:
            return
        
        # Clear existing schedules
        schedule.clear()
        
        if self.config.auto_start_enabled:
            # Schedule start at market open (9:15 AM) on weekdays
            schedule.every().monday.at("09:15").do(self._auto_start)
            schedule.every().tuesday.at("09:15").do(self._auto_start)
            schedule.every().wednesday.at("09:15").do(self._auto_start)
            schedule.every().thursday.at("09:15").do(self._auto_start)
            schedule.every().friday.at("09:15").do(self._auto_start)
        
        if self.config.auto_stop_enabled:
            # Schedule stop at market close (3:30 PM) on weekdays
            schedule.every().monday.at("15:30").do(self._auto_stop)
            schedule.every().tuesday.at("15:30").do(self._auto_stop)
            schedule.every().wednesday.at("15:30").do(self._auto_stop)
            schedule.every().thursday.at("15:30").do(self._auto_stop)
            schedule.every().friday.at("15:30").do(self._auto_stop)
        
        logger.info("Market operation schedules configured")
    
    def _auto_start(self):
        """Automatically start pipeline at market open"""
        logger.info("Auto-starting pipeline for market open")
        if not self.pipeline or not self.pipeline.running:
            self._start_pipeline()
    
    def _auto_stop(self):
        """Automatically stop pipeline at market close"""
        logger.info("Auto-stopping pipeline for market close")
        if self.pipeline and self.pipeline.running:
            self._stop_pipeline()
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Sleep for a short interval
                self.shutdown_event.wait(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
        
        logger.info("Scheduler loop stopped")
    
    def _health_monitoring_loop(self):
        """Health monitoring loop"""
        logger.info("Health monitoring loop started")
        
        while not self.shutdown_event.is_set():
            try:
                health_status = self._perform_health_check()
                
                # Handle unhealthy states
                if health_status in ["pipeline_stopped", "stale_data", "high_error_rate"] and self.config.restart_on_failure:
                    if self.restart_attempts < self.config.max_restart_attempts:
                        logger.warning(f"Pipeline unhealthy ({health_status}), attempting restart {self.restart_attempts + 1}")
                        self.restart_attempts += 1
                        self._restart_pipeline()
                    else:
                        logger.error(f"Maximum restart attempts ({self.config.max_restart_attempts}) reached")
                
                # Wait for next health check
                self.shutdown_event.wait(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
        
        logger.info("Health monitoring loop stopped")
    
    def start(self):
        """Start the scheduler service"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting pipeline scheduler service")
        
        self.running = True
        self.shutdown_event.clear()
        
        # Setup market operation schedules
        self._schedule_market_operations()
        
        # Start background threads
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.health_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        
        self.scheduler_thread.start()
        self.health_thread.start()
        
        # Auto-start pipeline if market is open
        if self.config.auto_start_enabled and self._is_market_open():
            logger.info("Market is open, auto-starting pipeline")
            self._start_pipeline()
        
        logger.info("Pipeline scheduler service started")
    
    def stop(self):
        """Stop the scheduler service"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping pipeline scheduler service")
        
        # Stop pipeline first
        if self.pipeline and self.pipeline.running:
            self._stop_pipeline()
        
        # Stop scheduler
        self.running = False
        self.shutdown_event.set()
        
        # Wait for threads
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        if self.health_thread:
            self.health_thread.join(timeout=5)
        
        logger.info("Pipeline scheduler service stopped")
    
    def run_api_server(self):
        """Run the FastAPI server"""
        uvicorn.run(
            self.app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info"
        )

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if 'scheduler' in globals():
        scheduler.stop()
    sys.exit(0)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pipeline scheduler service')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--api-port', type=int, default=8001, help='API server port')
    parser.add_argument('--no-auto-start', action='store_true', help='Disable auto-start')
    parser.add_argument('--no-auto-stop', action='store_true', help='Disable auto-stop')
    parser.add_argument('--health-interval', type=int, default=30, help='Health check interval in seconds')
    
    args = parser.parse_args()
    
    # Create configuration
    config = SchedulerConfig()
    config.api_port = args.api_port
    config.health_check_interval = args.health_interval
    
    if args.no_auto_start:
        config.auto_start_enabled = False
    if args.no_auto_stop:
        config.auto_stop_enabled = False
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start scheduler
    global scheduler
    scheduler = PipelineScheduler(config)
    
    try:
        # Start scheduler service
        scheduler.start()
        
        # Start API server (this blocks)
        logger.info(f"Starting API server on port {config.api_port}")
        scheduler.run_api_server()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scheduler.stop()

if __name__ == "__main__":
    main()

