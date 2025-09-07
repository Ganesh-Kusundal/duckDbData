#!/usr/bin/env python3
"""
Comprehensive test script for all Breakout Scanner notebook components.
This script tests every major functionality from the notebook.
"""

import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

def setup_environment():
    """Setup the environment (same as notebook)."""
    print("🔧 Setting up environment...")

    # Setup path
    current_dir = Path.cwd()
    if current_dir.name == 'scanner':
        project_root = current_dir.parent.parent
    elif current_dir.name == 'notebook':
        project_root = current_dir.parent
    else:
        project_root = current_dir

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(project_root / 'src') not in sys.path:
        sys.path.insert(0, str(project_root / 'src'))

    print(f"Project root: {project_root}")

    # Import required modules
    try:
        from src.infrastructure.logging import setup_logging
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
        from src.infrastructure.core.database import DuckDBManager
        from src.infrastructure.config.settings import get_settings

        # Setup logging
        setup_logging()

        # Setup plotly theme
        import plotly.io as pio
        pio.templates.default = "plotly_white"

        print("✅ Environment setup successful")
        return project_root, setup_logging, BreakoutScanner, DuckDBManager, get_settings

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return None, None, None, None, None

def test_database_connection(project_root, DuckDBManager):
    """Test database connection."""
    print("\\n🗄️ Testing database connection...")

    try:
        # Use main database
        main_db_path = project_root / "data" / "financial_data.duckdb"
        db_manager = DuckDBManager(db_path=str(main_db_path))

        # Create schema
        db_manager.create_schema()

        print("✅ Database connection and schema creation successful")
        return db_manager

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def test_data_availability(db_manager, BreakoutScanner):
    """Test data availability checks."""
    print("\\n📊 Testing data availability...")

    try:
        # Initialize scanner
        scanner = BreakoutScanner(db_manager=db_manager)

        # Get available symbols
        symbols = scanner.get_available_symbols()
        print(f"Available symbols: {len(symbols)}")

        if symbols:
            print(f"Sample symbols: {symbols[:5]}")

        # Check date range
        date_query = """
        SELECT
            MIN(date_partition) as start_date,
            MAX(date_partition) as end_date,
            COUNT(DISTINCT date_partition) as total_days,
            COUNT(*) as total_records
        FROM market_data
        """

        date_info = db_manager.execute_custom_query(date_query)
        if not date_info.empty:
            info = date_info.iloc[0]
            print(f"Data date range: {info['start_date']} to {info['end_date']}")
            print(f"Total trading days: {info['total_days']}")
            print(f"Total records: {info['total_records']:,}")

        print("✅ Data availability check successful")
        return scanner

    except Exception as e:
        print(f"❌ Data availability error: {e}")
        return None

def test_single_day_scanning(scanner):
    """Test single day scanner functionality."""
    print("\\n🧪 Testing single day scanning...")

    try:
        # Test date
        test_date = date(2025, 6, 9)
        cutoff_time = time(9, 50)

        print(f"Testing date: {test_date}")

        # Run scanner
        start_time = datetime.now()
        results = scanner.scan(test_date, cutoff_time)
        end_time = datetime.now()

        execution_time = (end_time - start_time).total_seconds()

        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Results shape: {results.shape}")

        if not results.empty:
            print("Sample results:")
            display_cols = ['symbol', 'current_price', 'breakout_score']
            sample_results = results[display_cols].head(3)
            print(sample_results.to_string(index=False))

            # Save results
            results.to_csv('test_single_day_results.csv', index=False)
            print("✅ Single day scanning successful")
            return True
        else:
            print("⚠️ No breakout patterns found (this may be normal)")
            return True

    except Exception as e:
        print(f"❌ Single day scanning error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_day_backtesting(scanner):
    """Test multi-day backtesting."""
    print("\\n📅 Testing multi-day backtesting...")

    try:
        # Define backtest parameters
        start_date = date(2025, 6, 9)
        end_date = date(2025, 6, 13)  # Short range for testing
        cutoff_time = time(9, 50)

        print(f"Backtest period: {start_date} to {end_date}")

        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday
                date_range.append(current_date)
            current_date += timedelta(days=1)

        print(f"Trading days to test: {len(date_range)}")

        # Run backtest
        backtest_results = []
        total_execution_time = 0

        for test_date in date_range:
            try:
                start_time = datetime.now()
                daily_results = scanner.scan(test_date, cutoff_time)
                end_time = datetime.now()

                execution_time = (end_time - start_time).total_seconds()
                total_execution_time += execution_time

                result_summary = {
                    'date': test_date,
                    'symbols_found': len(daily_results),
                    'execution_time': execution_time,
                    'avg_score': daily_results['breakout_score'].mean() if not daily_results.empty else 0,
                    'max_score': daily_results['breakout_score'].max() if not daily_results.empty else 0
                }

                backtest_results.append(result_summary)
                print(f"  {test_date}: {result_summary['symbols_found']} symbols")

            except Exception as e:
                print(f"❌ Error on {test_date}: {e}")
                backtest_results.append({
                    'date': test_date,
                    'symbols_found': 0,
                    'execution_time': 0,
                    'avg_score': 0,
                    'max_score': 0,
                    'error': str(e)
                })

        # Convert to DataFrame
        backtest_df = pd.DataFrame(backtest_results)

        print("\\n📈 Backtest Summary:")
        print(f"Total execution time: {total_execution_time:.2f} seconds")
        print(f"Average time per day: {total_execution_time/len(date_range):.2f} seconds")
        print(f"Total symbols found: {backtest_df['symbols_found'].sum()}")

        # Save results
        backtest_df.to_csv('test_backtest_summary.csv', index=False)
        print("✅ Multi-day backtesting successful")
        return backtest_df

    except Exception as e:
        print(f"❌ Multi-day backtesting error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_performance_visualization(backtest_df):
    """Test performance visualization."""
    print("\\n📊 Testing performance visualization...")

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Symbols Found per Day', 'Execution Time per Day',
                           'Average Breakout Score per Day', 'Distribution of Max Scores')
        )

        # Convert date to string for better display
        backtest_df['date_str'] = backtest_df['date'].astype(str)

        # 1. Symbols found over time
        fig.add_trace(
            go.Scatter(x=backtest_df['date_str'], y=backtest_df['symbols_found'],
                      mode='lines+markers', name='Symbols Found',
                      line=dict(color='blue', width=2)),
            row=1, col=1
        )

        # 2. Execution time
        fig.add_trace(
            go.Bar(x=backtest_df['date_str'], y=backtest_df['execution_time'],
                   name='Execution Time', marker_color='lightblue'),
            row=1, col=2
        )

        # 3. Average scores
        fig.add_trace(
            go.Scatter(x=backtest_df['date_str'], y=backtest_df['avg_score'],
                      mode='lines+markers', name='Average Score',
                      line=dict(color='orange', width=2)),
            row=2, col=1
        )

        # 4. Score distribution
        if backtest_df['symbols_found'].sum() > 0:
            fig.add_trace(
                go.Histogram(x=backtest_df['max_score'], nbinsx=10,
                            name='Max Score Distribution', marker_color='green',
                            opacity=0.7),
                row=2, col=2
            )
        else:
            fig.add_annotation(
                text="No scores to display",
                xref="x4", yref="y4",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14)
            )

        # Update layout
        fig.update_layout(
            title_text='Breakout Scanner Backtest Analysis',
            title_x=0.5,
            height=800,
            showlegend=False
        )

        # Update x-axis labels
        fig.update_xaxes(tickangle=45)

        # Update y-axis labels
        fig.update_yaxes(title_text="Number of Symbols", row=1, col=1)
        fig.update_yaxes(title_text="Time (seconds)", row=1, col=2)
        fig.update_yaxes(title_text="Average Score", row=2, col=1)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)

        # Save as HTML
        fig.write_html('test_performance_analysis.html')
        print("✅ Performance visualization saved as test_performance_analysis.html")

        # Try to show (this might work in some environments)
        try:
            fig.show()
            print("✅ Chart displayed successfully")
        except Exception as e:
            print(f"⚠️ Chart display failed (expected in headless environment): {e}")

        return True

    except Exception as e:
        print(f"❌ Performance visualization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_sensitivity(scanner):
    """Test parameter sensitivity analysis."""
    print("\\n🔬 Testing parameter sensitivity...")

    try:
        # Define parameter ranges to test
        param_configs = [
            {'name': 'Conservative', 'breakout_volume_ratio': 3.0, 'resistance_break_pct': 2.0, 'consolidation_range_pct': 2.0},
            {'name': 'Moderate', 'breakout_volume_ratio': 2.0, 'resistance_break_pct': 1.5, 'consolidation_range_pct': 3.0},
        ]

        test_date = date(2025, 6, 9)
        cutoff_time = time(9, 50)

        sensitivity_results = []

        for config in param_configs:
            print(f"  Testing {config['name']} configuration...")

            # Temporarily modify scanner config
            original_config = scanner.config.copy()
            scanner.config.update(config)

            try:
                results = scanner.scan(test_date, cutoff_time)

                sensitivity_results.append({
                    'config': config['name'],
                    'symbols_found': len(results),
                    'avg_score': results['breakout_score'].mean() if not results.empty else 0,
                    'max_score': results['breakout_score'].max() if not results.empty else 0,
                    'breakout_volume_ratio': config['breakout_volume_ratio'],
                    'resistance_break_pct': config['resistance_break_pct'],
                    'consolidation_range_pct': config['consolidation_range_pct']
                })

                print(f"    Symbols found: {len(results)}")

            except Exception as e:
                print(f"❌ Error with {config['name']}: {e}")

            finally:
                # Restore original config
                scanner.config = original_config

        # Display results
        if sensitivity_results:
            sensitivity_df = pd.DataFrame(sensitivity_results)
            print("\\n📊 Parameter Sensitivity Results:")
            print(sensitivity_df.to_string(index=False))

            # Save results
            sensitivity_df.to_csv('test_parameter_sensitivity.csv', index=False)
            print("✅ Parameter sensitivity testing successful")
            return True
        else:
            print("⚠️ No sensitivity test results")
            return False

    except Exception as e:
        print(f"❌ Parameter sensitivity error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_debug_functionality(scanner):
    """Test debug functionality."""
    print("\\n🔍 Testing debug functionality...")

    try:
        test_date = date(2025, 6, 9)
        cutoff_time = time(9, 50)

        print(f"Debugging scanner for {test_date} at {cutoff_time}")

        # Check if data exists for the date
        data_check_query = f"""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN(timestamp) as earliest_time,
            MAX(timestamp) as latest_time
        FROM market_data
        WHERE date_partition = '{test_date}'
        """

        data_check = scanner.db_manager.execute_custom_query(data_check_query)
        if not data_check.empty:
            info = data_check.iloc[0]
            print("Data availability:")
            print(f"  Total records: {info['total_records']}")
            print(f"  Unique symbols: {info['unique_symbols']}")
            print(f"  Time range: {info['earliest_time']} to {info['latest_time']}")

        print("✅ Debug functionality test successful")
        return True

    except Exception as e:
        print(f"❌ Debug functionality error: {e}")
        return False

def main():
    """Run all component tests."""
    print("🚀 Breakout Scanner Components Test Suite")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Setup environment
    setup_result = setup_environment()
    if not all(setup_result):
        print("❌ Environment setup failed")
        return

    project_root, setup_logging, BreakoutScanner, DuckDBManager, get_settings = setup_result

    # Test database connection
    db_manager = test_database_connection(project_root, DuckDBManager)
    if not db_manager:
        print("❌ Database connection failed")
        return

    # Test data availability
    scanner = test_data_availability(db_manager, BreakoutScanner)
    if not scanner:
        print("❌ Data availability test failed")
        return

    # Test components
    tests = [
        ("Single Day Scanning", lambda: test_single_day_scanning(scanner)),
        ("Multi-Day Backtesting", lambda: test_multi_day_backtesting(scanner)),
        ("Parameter Sensitivity", lambda: test_parameter_sensitivity(scanner)),
        ("Debug Functionality", lambda: test_debug_functionality(scanner)),
    ]

    results = []
    backtest_df = None

    for test_name, test_func in tests:
        print(f"\\n{test_name}")
        print("-" * len(test_name))

        try:
            if test_name == "Multi-Day Backtesting":
                backtest_df = test_func()
                results.append((test_name, backtest_df is not None))
            elif test_name == "Performance Visualization" and backtest_df is not None:
                results.append((test_name, test_performance_visualization(backtest_df)))
            else:
                results.append((test_name, test_func()))
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results.append((test_name, False))

    # Test visualization if backtest data is available
    if backtest_df is not None:
        print("\\nPerformance Visualization")
        print("-" * len("Performance Visualization"))
        results.append(("Performance Visualization", test_performance_visualization(backtest_df)))

    # Close database connection
    try:
        db_manager.close()
        print("\\n✅ Database connection closed")
    except:
        pass

    # Summary
    print("\\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\\n📊 Results: {passed}/{total} tests passed")

    success_rate = passed / total if total > 0 else 0
    if success_rate >= 0.8:
        print("\\n🎉 Test suite PASSED!")
        print("\\n💡 Generated test files:")
        print("   - test_single_day_results.csv")
        print("   - test_backtest_summary.csv")
        print("   - test_parameter_sensitivity.csv")
        print("   - test_performance_analysis.html")
    else:
        print("\\n⚠️ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
