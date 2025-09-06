#!/usr/bin/env python3
"""
Pipeline Monitor
===============

Real-time monitoring dashboard and alerting system for the data pipeline.
Provides comprehensive monitoring, alerting, and performance analysis.

Features:
- Real-time status monitoring
- Performance metrics and analytics
- Alert system with multiple channels
- Historical data analysis
- System health scoring
- Automated reporting

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
from pathlib import Path
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import requests
from dataclasses import dataclass, asdict
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
import threading

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Alert configuration"""
    email_enabled: bool = False
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = None
    
    slack_enabled: bool = False
    slack_webhook_url: str = ""
    
    # Alert thresholds
    max_error_rate: float = 0.05  # 5%
    max_stale_minutes: int = 5
    min_update_frequency: int = 2  # updates per minute during market hours
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []

@dataclass
class MonitoringMetrics:
    """Monitoring metrics"""
    timestamp: datetime
    pipeline_running: bool
    market_open: bool
    data_updates_per_minute: float
    indicator_updates_per_minute: float
    error_rate: float
    symbols_processed: int
    records_processed: int
    last_data_update: Optional[datetime]
    last_indicator_update: Optional[datetime]
    health_score: float  # 0-100
    
    def to_dict(self) -> Dict:
        return asdict(self)

class PipelineMonitor:
    """Comprehensive pipeline monitoring system"""
    
    def __init__(self, scheduler_api_url: str = "http://localhost:8001", alert_config: Optional[AlertConfig] = None):
        """Initialize the monitor"""
        self.scheduler_api_url = scheduler_api_url.rstrip('/')
        self.alert_config = alert_config or AlertConfig()
        
        # Monitoring data
        self.metrics_history: List[MonitoringMetrics] = []
        self.alerts_sent: List[Dict] = []
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Alert cooldown (prevent spam)
        self.alert_cooldown_minutes = 15
        
        # Running state
        self.running = False
        self.shutdown_event = threading.Event()
        
        logger.info("Pipeline monitor initialized")
    
    def _fetch_pipeline_status(self) -> Optional[Dict]:
        """Fetch current pipeline status from scheduler API"""
        try:
            response = requests.get(f"{self.scheduler_api_url}/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch pipeline status: {e}")
            return None
    
    def _calculate_health_score(self, status: Dict) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # Pipeline running (30 points)
        pipeline_status = status.get('pipeline', {})
        if not pipeline_status or not pipeline_status.get('running', False):
            score -= 30
        
        # Market hours compliance (20 points)
        market_open = status.get('market', {}).get('is_open', False)
        pipeline_running = pipeline_status.get('running', False)
        
        if market_open and not pipeline_running:
            score -= 20  # Should be running during market hours
        elif not market_open and pipeline_running:
            score -= 5   # Minor penalty for running outside market hours
        
        # Error rate (25 points)
        stats = pipeline_status.get('stats', {})
        total_operations = stats.get('data_updates', 0) + stats.get('indicator_updates', 0)
        if total_operations > 0:
            error_rate = stats.get('errors', 0) / total_operations
            if error_rate > 0.1:  # >10% error rate
                score -= 25
            elif error_rate > 0.05:  # >5% error rate
                score -= 15
            elif error_rate > 0.02:  # >2% error rate
                score -= 5
        
        # Data freshness (15 points)
        if market_open:
            last_update = stats.get('last_data_update')
            if last_update:
                try:
                    last_update_time = datetime.fromisoformat(last_update) if isinstance(last_update, str) else last_update
                    minutes_since_update = (datetime.now() - last_update_time).total_seconds() / 60
                    
                    if minutes_since_update > 10:
                        score -= 15
                    elif minutes_since_update > 5:
                        score -= 10
                    elif minutes_since_update > 2:
                        score -= 5
                except:
                    score -= 10  # Invalid timestamp
            else:
                score -= 15  # No update timestamp
        
        # Performance (10 points)
        symbols_processed = stats.get('symbols_processed', 0)
        if symbols_processed < 100 and market_open:  # Expect at least 100 symbols during market hours
            score -= 10
        elif symbols_processed < 50:
            score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _collect_metrics(self) -> Optional[MonitoringMetrics]:
        """Collect current monitoring metrics"""
        try:
            status = self._fetch_pipeline_status()
            if not status:
                return None
            
            pipeline_status = status.get('pipeline', {})
            scheduler_status = status.get('scheduler', {})
            market_status = status.get('market', {})
            stats = pipeline_status.get('stats', {})
            
            # Calculate rates
            data_updates = stats.get('data_updates', 0)
            indicator_updates = stats.get('indicator_updates', 0)
            
            # Get uptime for rate calculation
            start_time_str = stats.get('start_time')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                uptime_minutes = (datetime.now() - start_time).total_seconds() / 60
                data_updates_per_minute = data_updates / max(uptime_minutes, 1)
                indicator_updates_per_minute = indicator_updates / max(uptime_minutes, 1)
            else:
                data_updates_per_minute = 0
                indicator_updates_per_minute = 0
            
            # Calculate error rate
            total_operations = data_updates + indicator_updates
            error_rate = stats.get('errors', 0) / max(total_operations, 1)
            
            # Parse timestamps
            last_data_update = None
            last_indicator_update = None
            
            if stats.get('last_data_update'):
                try:
                    last_data_update = datetime.fromisoformat(stats['last_data_update']) if isinstance(stats['last_data_update'], str) else stats['last_data_update']
                except:
                    pass
            
            if stats.get('last_indicator_update'):
                try:
                    last_indicator_update = datetime.fromisoformat(stats['last_indicator_update']) if isinstance(stats['last_indicator_update'], str) else stats['last_indicator_update']
                except:
                    pass
            
            # Calculate health score
            health_score = self._calculate_health_score(status)
            
            metrics = MonitoringMetrics(
                timestamp=datetime.now(),
                pipeline_running=pipeline_status.get('running', False),
                market_open=market_status.get('is_open', False),
                data_updates_per_minute=data_updates_per_minute,
                indicator_updates_per_minute=indicator_updates_per_minute,
                error_rate=error_rate,
                symbols_processed=stats.get('symbols_processed', 0),
                records_processed=stats.get('records_processed', 0),
                last_data_update=last_data_update,
                last_indicator_update=last_indicator_update,
                health_score=health_score
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if alert should be sent (considering cooldown)"""
        last_alert = self.last_alert_times.get(alert_type)
        if last_alert:
            time_since_last = datetime.now() - last_alert
            if time_since_last.total_seconds() < self.alert_cooldown_minutes * 60:
                return False
        return True
    
    def _send_email_alert(self, subject: str, message: str):
        """Send email alert"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available")
            return
            
        if not self.alert_config.email_enabled or not self.alert_config.email_recipients:
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.alert_config.email_username
            msg['To'] = ', '.join(self.alert_config.email_recipients)
            msg['Subject'] = f"[Pipeline Alert] {subject}"
            
            body = f"""
Pipeline Alert
==============

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Alert: {subject}

Details:
{message}

---
This is an automated alert from the Pipeline Monitoring System.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.alert_config.email_smtp_server, self.alert_config.email_smtp_port)
            server.starttls()
            server.login(self.alert_config.email_username, self.alert_config.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, subject: str, message: str):
        """Send Slack alert"""
        if not self.alert_config.slack_enabled or not self.alert_config.slack_webhook_url:
            return
        
        try:
            payload = {
                "text": f"🚨 Pipeline Alert: {subject}",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {
                                "title": "Time",
                                "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            },
                            {
                                "title": "Details",
                                "value": message,
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(self.alert_config.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack alert sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_alert(self, alert_type: str, subject: str, message: str):
        """Send alert through configured channels"""
        if not self._should_send_alert(alert_type):
            logger.debug(f"Alert {alert_type} skipped due to cooldown")
            return
        
        # Send through all enabled channels
        if self.alert_config.email_enabled:
            self._send_email_alert(subject, message)
        
        if self.alert_config.slack_enabled:
            self._send_slack_alert(subject, message)
        
        # Record alert
        alert_record = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'subject': subject,
            'message': message
        }
        self.alerts_sent.append(alert_record)
        self.last_alert_times[alert_type] = datetime.now()
        
        logger.warning(f"Alert sent: {subject}")
    
    def _check_alerts(self, metrics: MonitoringMetrics):
        """Check for alert conditions"""
        # Pipeline down during market hours
        if metrics.market_open and not metrics.pipeline_running:
            self._send_alert(
                'pipeline_down',
                'Pipeline Down During Market Hours',
                f'The data pipeline is not running while the market is open.\n'
                f'Market Status: Open\n'
                f'Pipeline Status: Stopped\n'
                f'Health Score: {metrics.health_score:.1f}/100'
            )
        
        # High error rate
        if metrics.error_rate > self.alert_config.max_error_rate:
            self._send_alert(
                'high_error_rate',
                'High Error Rate Detected',
                f'Error rate is above threshold.\n'
                f'Current Error Rate: {metrics.error_rate:.2%}\n'
                f'Threshold: {self.alert_config.max_error_rate:.2%}\n'
                f'Health Score: {metrics.health_score:.1f}/100'
            )
        
        # Stale data during market hours
        if metrics.market_open and metrics.last_data_update:
            minutes_since_update = (datetime.now() - metrics.last_data_update).total_seconds() / 60
            if minutes_since_update > self.alert_config.max_stale_minutes:
                self._send_alert(
                    'stale_data',
                    'Stale Data Detected',
                    f'Data has not been updated recently during market hours.\n'
                    f'Last Update: {metrics.last_data_update.strftime("%H:%M:%S")}\n'
                    f'Minutes Since Update: {minutes_since_update:.1f}\n'
                    f'Threshold: {self.alert_config.max_stale_minutes} minutes\n'
                    f'Health Score: {metrics.health_score:.1f}/100'
                )
        
        # Low health score
        if metrics.health_score < 50:
            self._send_alert(
                'low_health_score',
                'Low System Health Score',
                f'System health score is critically low.\n'
                f'Current Health Score: {metrics.health_score:.1f}/100\n'
                f'Pipeline Running: {metrics.pipeline_running}\n'
                f'Market Open: {metrics.market_open}\n'
                f'Error Rate: {metrics.error_rate:.2%}\n'
                f'Symbols Processed: {metrics.symbols_processed}'
            )
        
        # Low update frequency during market hours
        if metrics.market_open and metrics.data_updates_per_minute < self.alert_config.min_update_frequency:
            self._send_alert(
                'low_update_frequency',
                'Low Update Frequency',
                f'Data update frequency is below expected rate during market hours.\n'
                f'Current Rate: {metrics.data_updates_per_minute:.2f} updates/minute\n'
                f'Expected Rate: {self.alert_config.min_update_frequency} updates/minute\n'
                f'Health Score: {metrics.health_score:.1f}/100'
            )
    
    def _generate_report(self, hours_back: int = 24) -> str:
        """Generate performance report"""
        if not self.metrics_history:
            return "No metrics data available for report generation."
        
        # Filter metrics for the specified time period
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return f"No metrics data available for the last {hours_back} hours."
        
        # Calculate statistics
        df = pd.DataFrame([m.to_dict() for m in recent_metrics])
        
        avg_health_score = df['health_score'].mean()
        min_health_score = df['health_score'].min()
        max_health_score = df['health_score'].max()
        
        avg_error_rate = df['error_rate'].mean()
        max_error_rate = df['error_rate'].max()
        
        total_symbols = df['symbols_processed'].max()
        total_records = df['records_processed'].max()
        
        uptime_percentage = (df['pipeline_running'].sum() / len(df)) * 100
        
        # Count alerts
        recent_alerts = [a for a in self.alerts_sent if a['timestamp'] >= cutoff_time]
        
        report = f"""
Pipeline Performance Report
==========================
Period: Last {hours_back} hours
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

HEALTH METRICS
--------------
Average Health Score: {avg_health_score:.1f}/100
Minimum Health Score: {min_health_score:.1f}/100
Maximum Health Score: {max_health_score:.1f}/100

PERFORMANCE METRICS
------------------
Pipeline Uptime: {uptime_percentage:.1f}%
Total Symbols Processed: {total_symbols:,}
Total Records Processed: {total_records:,}

ERROR METRICS
-------------
Average Error Rate: {avg_error_rate:.2%}
Maximum Error Rate: {max_error_rate:.2%}

ALERTS
------
Total Alerts: {len(recent_alerts)}
Alert Types: {', '.join(set(a['type'] for a in recent_alerts)) if recent_alerts else 'None'}

RECENT PERFORMANCE
-----------------
"""
        
        # Add recent metrics summary
        if len(recent_metrics) >= 10:
            last_10 = recent_metrics[-10:]
            for i, metric in enumerate(last_10, 1):
                report += f"{i:2d}. {metric.timestamp.strftime('%H:%M')} - Health: {metric.health_score:.0f}, "
                report += f"Running: {'Yes' if metric.pipeline_running else 'No'}, "
                report += f"Errors: {metric.error_rate:.1%}\n"
        
        return report
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                if metrics:
                    # Store metrics
                    self.metrics_history.append(metrics)
                    
                    # Keep only last 24 hours of metrics
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    self.metrics_history = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
                    
                    # Check for alerts
                    self._check_alerts(metrics)
                    
                    # Log current status
                    logger.info(f"Health Score: {metrics.health_score:.1f}, "
                              f"Pipeline: {'Running' if metrics.pipeline_running else 'Stopped'}, "
                              f"Market: {'Open' if metrics.market_open else 'Closed'}, "
                              f"Errors: {metrics.error_rate:.1%}")
                
                # Wait for next check
                self.shutdown_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.shutdown_event.wait(60)  # Wait longer on error
        
        logger.info("Monitoring loop stopped")
    
    def start(self):
        """Start the monitoring system"""
        if self.running:
            logger.warning("Monitor is already running")
            return
        
        logger.info("Starting pipeline monitor")
        
        self.running = True
        self.shutdown_event.clear()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Pipeline monitor started")
    
    def stop(self):
        """Stop the monitoring system"""
        if not self.running:
            logger.warning("Monitor is not running")
            return
        
        logger.info("Stopping pipeline monitor")
        
        self.running = False
        self.shutdown_event.set()
        
        # Wait for thread to finish
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.join(timeout=10)
        
        logger.info("Pipeline monitor stopped")
    
    def get_current_status(self) -> Dict:
        """Get current monitoring status"""
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'monitor_running': self.running,
            'metrics_collected': len(self.metrics_history),
            'alerts_sent': len(self.alerts_sent),
            'latest_metrics': latest_metrics.to_dict() if latest_metrics else None,
            'recent_alerts': [
                {
                    'timestamp': a['timestamp'].isoformat(),
                    'type': a['type'],
                    'subject': a['subject']
                }
                for a in self.alerts_sent[-5:]  # Last 5 alerts
            ]
        }
    
    def generate_daily_report(self) -> str:
        """Generate daily performance report"""
        return self._generate_report(hours_back=24)
    
    def generate_weekly_report(self) -> str:
        """Generate weekly performance report"""
        return self._generate_report(hours_back=168)  # 24 * 7

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pipeline monitoring system')
    parser.add_argument('--scheduler-url', default='http://localhost:8001', help='Scheduler API URL')
    parser.add_argument('--email-recipients', help='Comma-separated email recipients')
    parser.add_argument('--slack-webhook', help='Slack webhook URL')
    parser.add_argument('--report', choices=['daily', 'weekly'], help='Generate report and exit')
    
    args = parser.parse_args()
    
    # Create alert configuration
    alert_config = AlertConfig()
    
    if args.email_recipients:
        alert_config.email_enabled = True
        alert_config.email_recipients = [email.strip() for email in args.email_recipients.split(',')]
        # Email credentials should be set via environment variables
        alert_config.email_username = os.getenv('SMTP_USERNAME', '')
        alert_config.email_password = os.getenv('SMTP_PASSWORD', '')
    
    if args.slack_webhook:
        alert_config.slack_enabled = True
        alert_config.slack_webhook_url = args.slack_webhook
    
    # Create monitor
    monitor = PipelineMonitor(args.scheduler_url, alert_config)
    
    # Handle report generation
    if args.report:
        monitor.start()
        time.sleep(5)  # Give it time to collect some metrics
        
        if args.report == 'daily':
            report = monitor.generate_daily_report()
        else:
            report = monitor.generate_weekly_report()
        
        print(report)
        monitor.stop()
        return
    
    # Start monitoring
    try:
        monitor.start()
        
        logger.info("Pipeline monitor is running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        while monitor.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        monitor.stop()

if __name__ == "__main__":
    main()
