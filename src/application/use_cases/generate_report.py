"""
Generate Report Use Case
========================

Orchestrates report generation processes by coordinating between
domain services, repositories, and reporting frameworks.

This use case handles:
- Market scanning reports
- Data quality reports
- Performance analytics reports
- Trading signal reports
- Custom report generation
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class ReportType(Enum):
    """Types of reports that can be generated."""
    MARKET_SCAN = "market_scan"
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"
    TRADING_SIGNALS = "trading_signals"
    PORTFOLIO = "portfolio"
    CUSTOM = "custom"


@dataclass
class ReportRequest:
    """Request data for report generation."""
    report_type: ReportType
    title: str
    parameters: Dict[str, Any]
    date_range: Optional[tuple[date, date]] = None
    symbols: Optional[List[str]] = None
    output_format: str = "html"  # html, pdf, json, csv
    include_charts: bool = True


@dataclass
class ReportResult:
    """Result data from report generation."""
    report_type: ReportType
    report_title: str
    file_path: str
    generated_at: datetime
    execution_time_seconds: float
    metadata: Dict[str, Any]


class GenerateReportUseCase:
    """
    Use case for orchestrating report generation operations.

    This class coordinates the report generation workflow by:
    1. Validating report parameters
    2. Gathering required data
    3. Generating report content
    4. Formatting and saving reports
    5. Publishing report events
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        event_bus: EventBus
    ):
        """
        Initialize the generate report use case.

        Args:
            market_data_repo: Repository for market data access
            event_bus: Event bus for publishing report events
        """
        self.market_data_repo = market_data_repo
        self.event_bus = event_bus

        logger.info("GenerateReportUseCase initialized")

    def execute(self, request: ReportRequest) -> ReportResult:
        """
        Execute report generation for the given request.

        Args:
            request: Report request with parameters

        Returns:
            ReportResult containing report metadata

        Raises:
            ValueError: If report parameters are invalid
            RuntimeError: If report generation fails
        """
        start_time = datetime.now()
        logger.info(f"Starting {request.report_type.value} report generation: {request.title}")

        # Validate request
        self._validate_request(request)

        # Generate report based on type
        if request.report_type == ReportType.MARKET_SCAN:
            result = self._generate_market_scan_report(request)
        elif request.report_type == ReportType.DATA_QUALITY:
            result = self._generate_data_quality_report(request)
        elif request.report_type == ReportType.PERFORMANCE:
            result = self._generate_performance_report(request)
        elif request.report_type == ReportType.TRADING_SIGNALS:
            result = self._generate_trading_signals_report(request)
        elif request.report_type == ReportType.PORTFOLIO:
            result = self._generate_portfolio_report(request)
        elif request.report_type == ReportType.CUSTOM:
            result = self._generate_custom_report(request)
        else:
            raise ValueError(f"Unsupported report type: {request.report_type}")

        execution_time = (datetime.now() - start_time).total_seconds()

        final_result = ReportResult(
            report_type=request.report_type,
            report_title=request.title,
            file_path=result['file_path'],
            generated_at=start_time,
            execution_time_seconds=execution_time,
            metadata=result['metadata']
        )

        # Publish completion event
        self._publish_report_generated_event(final_result)

        logger.info(f"Report generated: {final_result.file_path} in {execution_time:.2f}s")

        return final_result

    def _generate_market_scan_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate market scan report.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating market scan report")

        # Extract parameters
        scan_date = request.parameters.get('scan_date', date.today())
        scanner_types = request.parameters.get('scanner_types', [])
        symbols = request.symbols or self.market_data_repo.get_active_symbols()

        # Gather scan data
        scan_data = []
        for symbol in symbols:
            try:
                # Get recent market data
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=scan_date,
                    end_date=scan_date
                )

                if not data.empty:
                    latest = data.iloc[-1]
                    scan_data.append({
                        'symbol': symbol,
                        'close': latest.get('close', 0),
                        'volume': latest.get('volume', 0),
                        'change_pct': latest.get('price_change_pct', 0)
                    })
            except Exception as e:
                logger.warning(f"Failed to get data for {symbol}: {e}")

        # Generate report content
        report_content = self._create_market_scan_html(
            request.title, scan_data, scan_date, scanner_types
        )

        # Save report
        file_path = self._save_report(
            report_content,
            f"market_scan_report_{scan_date.strftime('%Y%m%d')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'symbols_analyzed': len(scan_data),
                'scan_date': scan_date.isoformat(),
                'scanner_types': scanner_types
            }
        }

    def _generate_data_quality_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate data quality report.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating data quality report")

        symbols = request.symbols or self.market_data_repo.get_all_symbols()
        start_date, end_date = request.date_range or (date.today().replace(day=1), date.today())

        quality_stats = []

        for symbol in symbols:
            try:
                # Get data quality metrics
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                if not data.empty:
                    stats = {
                        'symbol': symbol,
                        'total_records': len(data),
                        'null_count': data.isnull().sum().sum(),
                        'completeness': (1 - data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100,
                        'date_range': f"{start_date} to {end_date}"
                    }
                    quality_stats.append(stats)
            except Exception as e:
                logger.warning(f"Failed to get quality stats for {symbol}: {e}")

        # Generate report content
        report_content = self._create_data_quality_html(request.title, quality_stats)

        # Save report
        file_path = self._save_report(
            report_content,
            f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'symbols_analyzed': len(quality_stats),
                'date_range': f"{start_date} to {end_date}",
                'avg_completeness': sum(s['completeness'] for s in quality_stats) / len(quality_stats) if quality_stats else 0
            }
        }

    def _generate_performance_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate performance analytics report.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating performance report")

        symbols = request.symbols or self.market_data_repo.get_active_symbols()
        start_date, end_date = request.date_range or (date.today().replace(month=1), date.today())

        performance_data = []

        for symbol in symbols:
            try:
                # Get performance data
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                if len(data) > 1:
                    start_price = data.iloc[0]['close']
                    end_price = data.iloc[-1]['close']
                    total_return = ((end_price - start_price) / start_price) * 100

                    # Calculate volatility
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std() * (252 ** 0.5) * 100  # Annualized volatility

                    performance_data.append({
                        'symbol': symbol,
                        'start_price': start_price,
                        'end_price': end_price,
                        'total_return_pct': total_return,
                        'volatility_pct': volatility,
                        'period_days': len(data)
                    })
            except Exception as e:
                logger.warning(f"Failed to calculate performance for {symbol}: {e}")

        # Sort by total return
        performance_data.sort(key=lambda x: x['total_return_pct'], reverse=True)

        # Generate report content
        report_content = self._create_performance_html(request.title, performance_data, start_date, end_date)

        # Save report
        file_path = self._save_report(
            report_content,
            f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'symbols_analyzed': len(performance_data),
                'date_range': f"{start_date} to {end_date}",
                'top_performer': performance_data[0]['symbol'] if performance_data else None,
                'avg_return': sum(p['total_return_pct'] for p in performance_data) / len(performance_data) if performance_data else 0
            }
        }

    def _generate_trading_signals_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate trading signals report.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating trading signals report")

        # This would integrate with scanner results
        # For now, create a placeholder structure
        signals_data = request.parameters.get('signals_data', [])

        # Generate report content
        report_content = self._create_trading_signals_html(request.title, signals_data)

        # Save report
        file_path = self._save_report(
            report_content,
            f"trading_signals_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'total_signals': len(signals_data),
                'signal_types': list(set(s.get('type', 'unknown') for s in signals_data))
            }
        }

    def _generate_portfolio_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate portfolio analysis report.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating portfolio report")

        # Portfolio holdings would come from parameters
        holdings = request.parameters.get('holdings', [])

        # Generate report content
        report_content = self._create_portfolio_html(request.title, holdings)

        # Save report
        file_path = self._save_report(
            report_content,
            f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'total_holdings': len(holdings),
                'total_value': sum(h.get('value', 0) for h in holdings)
            }
        }

    def _generate_custom_report(self, request: ReportRequest) -> Dict[str, Any]:
        """
        Generate custom report based on parameters.

        Args:
            request: Report request parameters

        Returns:
            Dictionary with report generation results
        """
        logger.info("Generating custom report")

        # Custom report logic based on parameters
        custom_data = request.parameters.get('data', [])
        template = request.parameters.get('template', 'default')

        # Generate report content
        report_content = self._create_custom_html(request.title, custom_data, template)

        # Save report
        file_path = self._save_report(
            report_content,
            f"custom_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.output_format
        )

        return {
            'file_path': file_path,
            'metadata': {
                'template': template,
                'data_points': len(custom_data)
            }
        }

    def _create_market_scan_html(self, title: str, scan_data: List[Dict], scan_date: date, scanner_types: List[str]) -> str:
        """Create HTML content for market scan report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #e8f4f8; padding: 15px; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Scan Date: {scan_date}</p>
                <p>Scanner Types: {', '.join(scanner_types) if scanner_types else 'All'}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Total symbols scanned: {len(scan_data)}</p>
            </div>

            <h2>Scan Results</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Close Price</th>
                    <th>Volume</th>
                    <th>Change %</th>
                </tr>
        """

        for item in scan_data:
            change_class = "positive" if item['change_pct'] >= 0 else "negative"
            html += f"""
                <tr>
                    <td>{item['symbol']}</td>
                    <td>{item['close']:.2f}</td>
                    <td>{item['volume']:,}</td>
                    <td class="{change_class}">{item['change_pct']:.2f}%</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _create_data_quality_html(self, title: str, quality_stats: List[Dict]) -> str:
        """Create HTML content for data quality report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #e8f4f8; padding: 15px; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .bad {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Total symbols analyzed: {len(quality_stats)}</p>
            </div>

            <h2>Data Quality Metrics</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Total Records</th>
                    <th>Null Count</th>
                    <th>Completeness %</th>
                </tr>
        """

        for stat in quality_stats:
            completeness_class = (
                "good" if stat['completeness'] >= 95 else
                "warning" if stat['completeness'] >= 80 else
                "bad"
            )
            html += f"""
                <tr>
                    <td>{stat['symbol']}</td>
                    <td>{stat['total_records']:,}</td>
                    <td>{stat['null_count']:,}</td>
                    <td class="{completeness_class}">{stat['completeness']:.1f}%</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _create_performance_html(self, title: str, performance_data: List[Dict], start_date: date, end_date: date) -> str:
        """Create HTML content for performance report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #e8f4f8; padding: 15px; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Period: {start_date} to {end_date}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Total symbols analyzed: {len(performance_data)}</p>
            </div>

            <h2>Performance Results</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Start Price</th>
                    <th>End Price</th>
                    <th>Total Return %</th>
                    <th>Volatility %</th>
                </tr>
        """

        for perf in performance_data:
            return_class = "positive" if perf['total_return_pct'] >= 0 else "negative"
            html += f"""
                <tr>
                    <td>{perf['symbol']}</td>
                    <td>{perf['start_price']:.2f}</td>
                    <td>{perf['end_price']:.2f}</td>
                    <td class="{return_class}">{perf['total_return_pct']:.2f}%</td>
                    <td>{perf['volatility_pct']:.2f}%</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _create_trading_signals_html(self, title: str, signals_data: List[Dict]) -> str:
        """Create HTML content for trading signals report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <h2>Trading Signals</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Signal Type</th>
                    <th>Price</th>
                    <th>Timestamp</th>
                </tr>
        """

        for signal in signals_data:
            html += f"""
                <tr>
                    <td>{signal.get('symbol', 'N/A')}</td>
                    <td>{signal.get('type', 'N/A')}</td>
                    <td>{signal.get('price', 'N/A')}</td>
                    <td>{signal.get('timestamp', 'N/A')}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _create_portfolio_html(self, title: str, holdings: List[Dict]) -> str:
        """Create HTML content for portfolio report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <h2>Portfolio Holdings</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Shares</th>
                    <th>Price</th>
                    <th>Value</th>
                </tr>
        """

        for holding in holdings:
            html += f"""
                <tr>
                    <td>{holding.get('symbol', 'N/A')}</td>
                    <td>{holding.get('shares', 0)}</td>
                    <td>{holding.get('price', 0):.2f}</td>
                    <td>{holding.get('value', 0):.2f}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _create_custom_html(self, title: str, custom_data: List[Dict], template: str) -> str:
        """Create HTML content for custom report."""
        html = f"""
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Template: {template}</p>
            </div>

            <h2>Custom Data</h2>
            <pre>{custom_data}</pre>
        </body>
        </html>
        """

        return html

    def _save_report(self, content: str, filename: str, output_format: str) -> str:
        """
        Save report to file.

        Args:
            content: Report content
            filename: Base filename
            output_format: Output format (html, json, etc.)

        Returns:
            Path to saved file
        """
        import os

        # Ensure reports directory exists
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)

        # Generate full file path
        file_path = os.path.join(reports_dir, f"{filename}.{output_format}")

        # Save content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    def _validate_request(self, request: ReportRequest):
        """
        Validate report request parameters.

        Args:
            request: Report request to validate

        Raises:
            ValueError: If validation fails
        """
        if not request.title.strip():
            raise ValueError("Report title cannot be empty")

        if request.output_format not in ['html', 'pdf', 'json', 'csv']:
            raise ValueError(f"Unsupported output format: {request.output_format}")

    def _publish_report_generated_event(self, result: ReportResult):
        """
        Publish report generation completion event to the event bus.

        Args:
            result: Report generation results to publish
        """
        event_data = {
            'report_type': result.report_type.value,
            'report_title': result.report_title,
            'file_path': result.file_path,
            'generated_at': result.generated_at.isoformat(),
            'execution_time_seconds': result.execution_time_seconds,
            'metadata': result.metadata
        }

        try:
            self.event_bus.publish({
                'event_type': 'report_generated',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.info("Published report generation event")
        except Exception as e:
            logger.error(f"Failed to publish report generation event: {e}")

    def get_available_report_types(self) -> List[str]:
        """
        Get list of available report types.

        Returns:
            List of report type names
        """
        return [rt.value for rt in ReportType]

    def get_report_templates(self, report_type: ReportType) -> List[str]:
        """
        Get available templates for a report type.

        Args:
            report_type: Type of report

        Returns:
            List of template names
        """
        # This could be expanded to return actual template files
        return ['default', 'detailed', 'summary']
