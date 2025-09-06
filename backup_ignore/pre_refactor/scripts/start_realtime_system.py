#!/usr/bin/env python3
"""
Real-Time System Starter
========================

Unified script to start the complete real-time data pipeline system.
Manages all components: data pipeline, scheduler, and monitoring.

Features:
- Single command to start entire system
- Component health checking
- Graceful shutdown handling
- Configuration management
- Service orchestration

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
from pathlib import Path
import logging
import signal
import time
import json
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional
import requests

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/realtime_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealTimeSystemManager:
    """Manages the complete real-time system"""
    
    def __init__(self):
        """Initialize the system manager"""
        self.processes = {}
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Create logs directory
        Path('logs').mkdir(exist_ok=True)
        
        logger.info("Real-time system manager initialized")
    
    def _start_scheduler(self, api_port: int = 8001) -> bool:
        """Start the pipeline scheduler service"""
        try:
            logger.info("Starting pipeline scheduler...")
            
            # Use conda environment python to ensure all dependencies are available
            conda_env_python = "/Users/apple/miniforge/envs/duckdb_infra/bin/python"
            cmd = [
                conda_env_python, 
                'scripts/pipeline_scheduler.py',
                '--api-port', str(api_port)
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            
            self.processes['scheduler'] = process
            
            # Wait a moment and check if it started successfully
            time.sleep(3)
            
            if process.poll() is None:  # Still running
                logger.info(f"Pipeline scheduler started (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Scheduler failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
    
    def _start_monitor(self, scheduler_url: str = "http://localhost:8001") -> bool:
        """Start the pipeline monitor"""
        try:
            logger.info("Starting pipeline monitor...")
            
            cmd = [
                sys.executable,
                'scripts/pipeline_monitor.py',
                '--scheduler-url', scheduler_url
            ]
            
            # Add email/slack configuration if available
            email_recipients = os.getenv('ALERT_EMAIL_RECIPIENTS')
            if email_recipients:
                cmd.extend(['--email-recipients', email_recipients])
            
            slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
            if slack_webhook:
                cmd.extend(['--slack-webhook', slack_webhook])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            
            self.processes['monitor'] = process
            
            # Wait a moment and check if it started successfully
            time.sleep(2)
            
            if process.poll() is None:  # Still running
                logger.info(f"Pipeline monitor started (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Monitor failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting monitor: {e}")
            return False
    
    def _check_scheduler_health(self, scheduler_url: str = "http://localhost:8001", timeout: int = 30) -> bool:
        """Check if scheduler is healthy and responsive"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{scheduler_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("Scheduler health check passed")
                    return True
            except:
                pass
            
            time.sleep(2)
        
        logger.error("Scheduler health check failed")
        return False
    
    def _wait_for_market_open(self) -> bool:
        """Wait for market to open if it's currently closed"""
        try:
            # Check current market status
            response = requests.get("http://localhost:8001/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                market_status = status.get('market', {})
                
                if market_status.get('is_open', False):
                    logger.info("Market is currently open")
                    return True
                
                next_open = market_status.get('next_open')
                if next_open:
                    logger.info(f"Market is closed. Next opening: {next_open}")
                    return True  # Don't wait, just inform
                
        except Exception as e:
            logger.warning(f"Could not check market status: {e}")
        
        return True
    
    def _monitor_processes(self):
        """Monitor running processes and restart if needed"""
        logger.info("Process monitoring started")
        
        while not self.shutdown_event.is_set():
            try:
                # Check each process
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:  # Process has terminated
                        logger.error(f"{name} process has terminated unexpectedly")
                        
                        # Try to restart
                        if name == 'scheduler':
                            logger.info(f"Attempting to restart {name}")
                            if self._start_scheduler():
                                logger.info(f"{name} restarted successfully")
                            else:
                                logger.error(f"Failed to restart {name}")
                        elif name == 'monitor':
                            logger.info(f"Attempting to restart {name}")
                            if self._start_monitor():
                                logger.info(f"{name} restarted successfully")
                            else:
                                logger.error(f"Failed to restart {name}")
                
                # Wait before next check
                self.shutdown_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                self.shutdown_event.wait(60)
        
        logger.info("Process monitoring stopped")
    
    def start(self, api_port: int = 8001, enable_monitor: bool = True) -> bool:
        """Start the complete real-time system"""
        if self.running:
            logger.warning("System is already running")
            return False
        
        logger.info("🚀 Starting Real-Time Data Pipeline System")
        logger.info("=" * 60)
        
        # Step 1: Start scheduler
        logger.info("Step 1: Starting Pipeline Scheduler")
        if not self._start_scheduler(api_port):
            logger.error("Failed to start scheduler. Aborting.")
            return False
        
        # Step 2: Wait for scheduler to be ready
        logger.info("Step 2: Waiting for Scheduler to be Ready")
        if not self._check_scheduler_health(f"http://localhost:{api_port}"):
            logger.error("Scheduler health check failed. Aborting.")
            self.stop()
            return False
        
        # Step 3: Start monitor (optional)
        if enable_monitor:
            logger.info("Step 3: Starting Pipeline Monitor")
            if not self._start_monitor(f"http://localhost:{api_port}"):
                logger.warning("Monitor failed to start, but continuing...")
        
        # Step 4: Check market status
        logger.info("Step 4: Checking Market Status")
        self._wait_for_market_open()
        
        # Step 5: Start process monitoring
        logger.info("Step 5: Starting Process Monitoring")
        self.running = True
        self.shutdown_event.clear()
        
        self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
        self.monitor_thread.start()
        
        # System started successfully
        logger.info("=" * 60)
        logger.info("✅ Real-Time Data Pipeline System Started Successfully!")
        logger.info("=" * 60)
        logger.info(f"📊 Scheduler API: http://localhost:{api_port}")
        logger.info(f"📊 Scheduler Status: http://localhost:{api_port}/status")
        logger.info(f"📊 Health Check: http://localhost:{api_port}/health")
        logger.info("=" * 60)
        
        return True
    
    def stop(self):
        """Stop the complete real-time system"""
        if not self.running:
            logger.warning("System is not running")
            return
        
        logger.info("🛑 Stopping Real-Time Data Pipeline System")
        logger.info("=" * 60)
        
        # Stop process monitoring
        self.running = False
        self.shutdown_event.set()
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=10)
        
        # Stop all processes
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name} (PID: {process.pid})")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    logger.info(f"{name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} did not stop gracefully, forcing...")
                    process.kill()
                    process.wait()
                    logger.info(f"{name} force stopped")
                    
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        self.processes.clear()
        
        logger.info("✅ Real-Time Data Pipeline System Stopped")
        logger.info("=" * 60)
    
    def get_status(self) -> Dict:
        """Get current system status"""
        status = {
            'system_running': self.running,
            'start_time': getattr(self, 'start_time', None),
            'processes': {}
        }
        
        for name, process in self.processes.items():
            status['processes'][name] = {
                'pid': process.pid,
                'running': process.poll() is None,
                'returncode': process.returncode
            }
        
        # Try to get scheduler status
        try:
            response = requests.get("http://localhost:8001/status", timeout=5)
            if response.status_code == 200:
                status['scheduler_status'] = response.json()
        except:
            status['scheduler_status'] = None
        
        return status
    
    def print_status(self):
        """Print current system status"""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("📊 REAL-TIME SYSTEM STATUS")
        print("=" * 60)
        print(f"System Running: {'✅ Yes' if status['system_running'] else '❌ No'}")
        
        print(f"\n📋 PROCESSES:")
        for name, proc_status in status['processes'].items():
            running_status = "✅ Running" if proc_status['running'] else "❌ Stopped"
            print(f"  {name.title()}: {running_status} (PID: {proc_status['pid']})")
        
        scheduler_status = status.get('scheduler_status')
        if scheduler_status:
            print(f"\n🔄 PIPELINE STATUS:")
            pipeline = scheduler_status.get('pipeline', {})
            market = scheduler_status.get('market', {})
            
            pipeline_running = "✅ Running" if pipeline.get('running', False) else "❌ Stopped"
            market_open = "✅ Open" if market.get('is_open', False) else "❌ Closed"
            
            print(f"  Pipeline: {pipeline_running}")
            print(f"  Market: {market_open}")
            
            stats = pipeline.get('stats', {})
            if stats:
                print(f"  Data Updates: {stats.get('data_updates', 0)}")
                print(f"  Indicator Updates: {stats.get('indicator_updates', 0)}")
                print(f"  Symbols Processed: {stats.get('symbols_processed', 0)}")
                print(f"  Records Processed: {stats.get('records_processed', 0)}")
                print(f"  Errors: {stats.get('errors', 0)}")
        
        print("=" * 60)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if 'system_manager' in globals():
        system_manager.stop()
    sys.exit(0)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time data pipeline system')
    parser.add_argument('--api-port', type=int, default=8001, help='Scheduler API port')
    parser.add_argument('--no-monitor', action='store_true', help='Disable monitoring')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    parser.add_argument('--stop', action='store_true', help='Stop running system')
    parser.add_argument('--monitor', action='store_true', help='Start interactive status monitor')
    parser.add_argument('--refresh', type=int, default=30, help='Monitor refresh interval (seconds)')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create system manager
    global system_manager
    system_manager = RealTimeSystemManager()
    
    # Handle status command
    if args.status:
        system_manager.print_status()
        return
    
    # Handle monitor command
    if args.monitor:
        logger.info("Starting interactive status monitor...")
        try:
            # Import and run the status monitor
            from scripts.pipeline_status import main as monitor_main
            import sys
            sys.argv = ['pipeline_status.py', '--refresh', str(args.refresh)]
            monitor_main()
        except ImportError:
            logger.error("Status monitor not available. Run: python scripts/pipeline_status.py")
        except KeyboardInterrupt:
            logger.info("Monitor stopped")
        return
    
    # Handle stop command
    if args.stop:
        logger.info("Stopping system...")
        # Try to stop via API first
        try:
            response = requests.post(f"http://localhost:{args.api_port}/stop", timeout=10)
            if response.status_code == 200:
                logger.info("System stopped via API")
            else:
                logger.warning("API stop failed, using process termination")
                system_manager.stop()
        except:
            logger.warning("Could not reach API, using process termination")
            system_manager.stop()
        return
    
    try:
        # Start the system
        success = system_manager.start(
            api_port=args.api_port,
            enable_monitor=not args.no_monitor
        )
        
        if not success:
            logger.error("Failed to start system")
            sys.exit(1)
        
        # Show initial status
        time.sleep(2)
        system_manager.print_status()
        
        logger.info("\n🎯 System is running. Use Ctrl+C to stop or:")
        logger.info(f"   • Status:  python scripts/start_realtime_system.py --status")
        logger.info(f"   • Monitor: python scripts/start_realtime_system.py --monitor")
        logger.info(f"   • Stop:    python scripts/start_realtime_system.py --stop")
        logger.info(f"   • API:     http://localhost:{args.api_port}")
        
        # Keep main thread alive
        while system_manager.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        system_manager.stop()

if __name__ == "__main__":
    main()
