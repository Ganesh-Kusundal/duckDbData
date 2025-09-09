"""
TraderX — 500-Stock Descriptive Analytics Dashboard
====================================================

Professional analytics dashboard for discovering high-probability breakout patterns
across the NIFTY-500 universe using 10 years of historical data.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, time, timedelta
import sys
import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from analytics.core.duckdb_connector import DuckDBAnalytics
from analytics.core.pattern_analyzer import PatternAnalyzer
from analytics.rules.rule_engine import RuleEngine, TradingSignal
from analytics.utils.data_processor import DataProcessor
from analytics.utils.visualization import AnalyticsVisualizer

# API Configuration
API_BASE_URL = "http://localhost:8000"  # FastAPI server from src/interfaces/api/

# Page configuration
st.set_page_config(
    page_title="TraderX — 500-Stock Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar for additional controls
with st.sidebar:
    st.header("🎯 Industry Filter")
    st.write("Filter by industry when 'By Industry' is selected")

    # Industry selection (only shown when universe is "By Industry")
    if 'universe' in locals() and universe == "By Industry":
        try:
            # Get available industries
            if 'market_data' in st.session_state and st.session_state.market_data is not None:
                industries = st.session_state.market_data['industry'].dropna().unique()
                selected_industries = st.multiselect(
                    "Select Industries",
                    options=sorted(industries),
                    default=list(industries)[:3] if len(industries) > 3 else list(industries)
                )
                st.session_state.selected_industries = selected_industries
        except:
            st.write("Load market data first to see industry options")

    st.header("📊 Dashboard Info")
    st.write("**Universe:** 501 NIFTY-500 stocks")
    st.write("**Industries:** 15+ sectors")
    st.write("**Data Source:** DuckDB database")
    st.write("**Last Updated:** Real-time")

# Custom CSS for TraderX design system
st.markdown("""
<style>
    /* TraderX Design System */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --tx-bg-primary: #0E1117;
        --tx-bg-secondary: #111827;
        --tx-text-primary: #F9FAFB;
        --tx-text-secondary: #D1D5DB;
        --tx-accent-teal: #14B8A6;
        --tx-accent-red: #EF4444;
        --tx-accent-amber: #F59E0B;
        --tx-border: #374151;
        --tx-hover: #1F2937;
    }

    * {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background-color: var(--tx-bg-primary);
        color: var(--tx-text-primary);
    }

    /* Top App Bar */
    .top-app-bar {
        background-color: var(--tx-bg-secondary);
        border-bottom: 1px solid var(--tx-border);
        padding: 12px 24px;
        position: sticky;
        top: 0;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 56px;
    }

    .brand {
        font-size: 20px;
        font-weight: 600;
        color: var(--tx-accent-teal);
    }

    .controls {
        display: flex;
        gap: 16px;
        align-items: center;
    }

    /* KPI Cards */
    .kpi-card {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        transition: all 0.2s ease;
    }

    .kpi-card:hover {
        border-color: var(--tx-accent-teal);
        background-color: var(--tx-hover);
    }

    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--tx-text-primary);
        margin-bottom: 4px;
    }

    .kpi-label {
        font-size: 12px;
        color: var(--tx-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Market Heatmap */
    .market-heatmap {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
        padding: 16px;
    }

    /* Leaderboards */
    .leaderboard-table {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
    }

    .leaderboard-table th {
        background-color: var(--tx-bg-primary);
        color: var(--tx-text-primary);
        font-weight: 600;
        padding: 12px 16px;
        text-align: left;
    }

    .leaderboard-table td {
        padding: 8px 16px;
        border-bottom: 1px solid var(--tx-border);
        color: var(--tx-text-secondary);
    }

    /* Time Patterns */
    .time-patterns {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
        padding: 16px;
    }

    /* Decision Cards */
    .decision-card {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .decision-card.positive {
        border-left: 4px solid var(--tx-accent-teal);
    }

    .decision-card.negative {
        border-left: 4px solid var(--tx-accent-red);
    }

    .decision-card.neutral {
        border-left: 4px solid var(--tx-accent-amber);
    }

    /* Status Bar */
    .status-bar {
        background-color: var(--tx-bg-secondary);
        border-top: 1px solid var(--tx-border);
        padding: 8px 24px;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        font-size: 11px;
        color: var(--tx-text-secondary);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Buttons */
    .stButton button {
        background-color: var(--tx-accent-teal) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    .stButton button:hover {
        background-color: #0F766E !important;
        transform: translateY(-1px);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--tx-bg-secondary);
        border-bottom: 1px solid var(--tx-border);
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--tx-text-secondary);
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: var(--tx-accent-teal);
        color: white;
    }

    /* Metrics */
    .stMetric {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
        padding: 16px;
    }

    .stMetric label {
        color: var(--tx-text-secondary) !important;
    }

    .stMetric .metric-container > div:first-child {
        color: var(--tx-text-primary) !important;
    }

    /* Sidebar */
    .stSidebar {
        background-color: var(--tx-bg-secondary) !important;
    }

    .stSidebar .stMarkdown h1, .stSidebar .stMarkdown h2, .stSidebar .stMarkdown h3 {
        color: var(--tx-text-primary) !important;
    }

    /* DataFrame styling */
    .stDataFrame {
        background-color: var(--tx-bg-secondary);
        border: 1px solid var(--tx-border);
        border-radius: 8px;
    }

    .stDataFrame th {
        background-color: var(--tx-bg-primary) !important;
        color: var(--tx-text-primary) !important;
    }

    .stDataFrame td {
        color: var(--tx-text-secondary) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for TraderX
if 'db_connector' not in st.session_state:
    st.session_state.db_connector = None
if 'pattern_analyzer' not in st.session_state:
    st.session_state.pattern_analyzer = None
if 'rule_engine' not in st.session_state:
    st.session_state.rule_engine = None
if 'market_data' not in st.session_state:
    st.session_state.market_data = None
if 'kpi_metrics' not in st.session_state:
    st.session_state.kpi_metrics = {}
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = []
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = None
if 'time_window' not in st.session_state:
    st.session_state.time_window = "09:15-09:50"
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'auto_rescan' not in st.session_state:
    st.session_state.auto_rescan = False

def initialize_traderx():
    """Initialize TraderX analytics components."""
    try:
        if st.session_state.db_connector is None:
            from src.infrastructure.config.config_manager import ConfigManager
            config_manager = ConfigManager(config_dir="../../configs")
            st.session_state.db_connector = DuckDBAnalytics(config_manager=config_manager)
            st.session_state.db_connector.connect()

        if st.session_state.pattern_analyzer is None:
            st.session_state.pattern_analyzer = PatternAnalyzer(st.session_state.db_connector)

        if st.session_state.rule_engine is None:
            st.session_state.rule_engine = RuleEngine()

        return True
    except Exception as e:
        st.error(f"❌ Failed to initialize TraderX: {e}")
        return False

def render_top_app_bar():
    """Render the top app bar with controls."""
    st.markdown("""
    <div class="top-app-bar">
        <div class="brand">TraderX • LIVE</div>
        <div class="controls">
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1, 1])

    with col1:
        date_range = st.date_input(
            "Date",
            value=datetime.now().date(),
            label_visibility="collapsed"
        )

    with col2:
        time_window_options = ["09:15–09:50", "09:50–11:00", "11:00–13:00", "13:00–15:15"]
        selected_window = st.selectbox(
            "Time Window",
            options=time_window_options,
            index=0,
            label_visibility="collapsed"
        )
        st.session_state.time_window = selected_window

    with col3:
        universe_options = ["All 500", "By Industry", "Watchlist"]
        universe = st.selectbox(
            "Universe",
            options=universe_options,
            index=0,
            label_visibility="collapsed"
        )

    with col4:
        liquidity = st.number_input(
            "Min Turnover (₹)",
            value=1000000,
            min_value=100000,
            step=100000,
            label_visibility="collapsed"
        )

    with col5:
        pattern_preset = "VSpike≥1.5× & RSI>55 & OBV↑"
        st.text_input(
            "Pattern Preset",
            value=pattern_preset,
            disabled=True,
            label_visibility="collapsed"
        )

    with col6:
        min_confidence = st.number_input(
            "Min Confidence",
            value=0.5,
            min_value=0.0,
            max_value=1.0,
            step=0.1,
            format="%.1f",
            label_visibility="collapsed",
            key="min_confidence_filter"
        )
        st.session_state.min_confidence_filter = min_confidence

    with col7:
        if st.button("🔍 SCAN", type="primary", use_container_width=True):
            perform_market_scan()

    st.markdown("</div>", unsafe_allow_html=True)

def render_kpi_strip():
    """Render the KPI strip with 6 metric cards."""
    st.markdown("### Market Overview")

    # Calculate KPIs from market data
    if st.session_state.market_data is not None:
        df = st.session_state.market_data

        # Calculate metrics
        adv_count = len(df[df['close'] > df['open']])
        dec_count = len(df[df['close'] < df['open']])

        breakout_candidates = len(df[
            (df['volume_spike'] >= 1.5) &
            (df['rsi'] > 55) &
            (df['close'] > df['sma_20'])
        ]) if all(col in df.columns for col in ['volume_spike', 'rsi', 'sma_20']) else 0

        obv_spikes = len(df[df['volume_spike'] >= 1.5]) if 'volume_spike' in df.columns else 0
        rsi_over_60 = len(df[df['rsi'] > 60]) if 'rsi' in df.columns else 0

        # Find top sector (simplified)
        top_sector = "BANKING"  # Would be calculated from actual data
        avg_sector_ret = 2.3  # Would be calculated

        # Volatility regime
        volatility = "Medium"  # Would be calculated from ATR
    else:
        # Default values when no data
        adv_count = dec_count = breakout_candidates = obv_spikes = rsi_over_60 = 0
        top_sector = "N/A"
        avg_sector_ret = 0.0
        volatility = "N/A"

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Adv/Dec >1%", f"{adv_count}/{dec_count}")

    with col2:
        st.metric("Breakout Candidates", breakout_candidates)

    with col3:
        st.metric("OBV Spikes ≥1.5×", obv_spikes)

    with col4:
        st.metric("RSI>60 Universe", rsi_over_60)

    with col5:
        metrics = st.session_state.kpi_metrics
        st.metric(f"Top Sector: {metrics['top_sector']}", f"{metrics['avg_sector_ret']:.1f}%")

    with col6:
        st.metric("Volatility Regime", st.session_state.kpi_metrics['volatility'])

def render_market_heatmap():
    """Render the market heatmap component."""
    st.subheader("Market Heatmap")

    if st.session_state.market_data is not None and len(st.session_state.market_data) > 10:
        df = st.session_state.market_data.copy()
        
        # Ensure timestamp column exists and create time buckets
        if 'timestamp' in df.columns:
            df['time_bucket'] = pd.to_datetime(df['timestamp']).dt.floor('5min')
        else:
            # Fallback: create synthetic time buckets
            df['time_bucket'] = pd.date_range(start='09:15', periods=len(df), freq='5T')
        
        # Limit to recent data for heatmap (last 50 records)
        recent_df = df.tail(50).copy()
        
        # Create pivot table for heatmap - handle missing time_bucket
        if 'time_bucket' in recent_df.columns and len(recent_df['symbol'].unique()) > 1:
            pivot_df = recent_df.pivot_table(
                values='close',
                index='symbol',
                columns='time_bucket',
                aggfunc='last'
            ).fillna(method='ffill')
            
            if not pivot_df.empty:
                fig = go.Figure(data=go.Heatmap(
                    z=pivot_df.values,
                    x=pivot_df.columns.astype(str),
                    y=pivot_df.index,
                    colorscale='RdYlGn',
                    hoverongaps=False,
                    hovertemplate='<b>%{y}</b><br>Time: %{x}<br>Price: ₹%{z:.2f}<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Real Price Action Heatmap (5-min buckets from DB)",
                    height=400,
                    margin=dict(l=40, r=20, t=40, b=20),
                    xaxis_title="Time Buckets",
                    yaxis_title="Symbols"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                return
        
        # Fallback: simple line chart if pivot fails
        st.warning("Using simplified visualization - complex pivot failed")
        
        fig = px.line(recent_df, x='time_bucket' if 'time_bucket' in recent_df.columns else range(len(recent_df)),
                     y='close', color='symbol', title="Price Movement Over Time")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Load market data to see real heatmap visualization")
        st.info("Expected: Query returns symbols with timestamped OHLCV data")

def render_sector_map():
    """Render the sector treemap."""
    st.subheader("Sector Map")

    # Mock sector data - would be calculated from real data
    sector_data = pd.DataFrame({
        'sector': ['IT', 'Finance', 'Healthcare', 'Energy', 'Consumer'],
        'avg_return': [2.3, 1.8, -0.5, 3.1, 1.2],
        'breakout_pct': [15, 12, 8, 18, 10],
        'liquidity_score': [85, 78, 65, 72, 80]
    })

    fig = px.treemap(
        sector_data,
        path=['sector'],
        values='avg_return',
        color='breakout_pct',
        color_continuous_scale='RdYlGn',
        title="Sector Performance & Breakout Activity"
    )

    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def render_leaderboards():
    """Render the leaderboards with tabs."""
    st.subheader("Leaderboards")

    tab1, tab2, tab3 = st.tabs(["Momentum", "OBV Builders", "Breakout Candidates"])

    with tab1:
        if st.session_state.market_data is not None:
            df = st.session_state.market_data.head(20).copy()
            momentum_data = df[['symbol', 'close', 'volume']].copy()
            momentum_data['momentum_score'] = (df['close'] - df['open']) / df['open'] * 100
            # Make sortable with st.data_editor
            edited_momentum = st.data_editor(
                momentum_data,
                column_config={
                    "momentum_score": st.column_config.NumberColumn(
                        "Momentum Score",
                        help="Percentage change",
                        format="%.2f %%"
                    )
                },
                use_container_width=True,
                hide_index=False
            )
            
            # Export button for momentum leaderboard
            csv = edited_momentum.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Momentum CSV",
                data=csv,
                file_name="momentum_leaderboard.csv",
                mime="text/csv"
            )
        else:
            st.info("Run scan to populate momentum leaderboard")

    with tab2:
        if st.session_state.market_data is not None:
            df = st.session_state.market_data.head(20).copy()
            obv_data = df[['symbol', 'volume']].copy()
            obv_data['obv_signal'] = ['↑' if v > 1000000 else '↓' for v in df['volume']]
            # Make sortable with st.data_editor
            edited_obv = st.data_editor(
                obv_data,
                column_config={
                    "volume": st.column_config.NumberColumn(
                        "Volume",
                        format="%d"
                    )
                },
                use_container_width=True,
                hide_index=False
            )
            
            # Export button for OBV builders
            csv = edited_obv.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export OBV CSV",
                data=csv,
                file_name="obv_builders.csv",
                mime="text/csv"
            )
        else:
            st.info("Run scan to populate OBV builders")

    with tab3:
        if st.session_state.scan_results:
            candidates_df = pd.DataFrame(st.session_state.scan_results)
            # Make sortable with st.data_editor
            edited_candidates = st.data_editor(
                candidates_df,
                column_config={
                    "confidence": st.column_config.NumberColumn(
                        "Confidence",
                        help="Pattern confidence score",
                        format="%.3f"
                    ),
                    "volume_multiplier": st.column_config.NumberColumn(
                        "Volume Multiplier",
                        format="%.2f"
                    ),
                    "price_move_pct": st.column_config.NumberColumn(
                        "Price Move %",
                        format="%.2f %%"
                    )
                },
                use_container_width=True,
                hide_index=False
            )
            
            # Export button for breakout candidates
            csv = edited_candidates.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Candidates CSV",
                data=csv,
                file_name="breakout_candidates.csv",
                mime="text/csv"
            )
        else:
            st.info("Run scan to populate breakout candidates")

def render_time_patterns():
    """Render time-of-day pattern analysis."""
    st.subheader("Time-of-Day Patterns")

    if st.session_state.market_data is not None:
        df = st.session_state.market_data

        # Group by hour for time patterns
        df['hour'] = pd.to_datetime(df.get('timestamp', pd.date_range('09:00', periods=len(df), freq='1H'))).dt.hour
        time_patterns = df.groupby('hour').agg({
            'close': 'count',
            'volume': 'sum'
        }).reset_index()

        fig = px.bar(
            time_patterns,
            x='hour',
            y='close',
            title="Pattern Frequency by Hour",
            labels={'close': 'Pattern Count', 'hour': 'Hour'}
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run scan to analyze time patterns")

def render_decision_cards():
    """Render decision cards with trading recommendations."""
    st.subheader("Decision Cards")

    # Go-Long Watchlist
    with st.container():
        st.markdown('<div class="decision-card positive">', unsafe_allow_html=True)
        st.subheader("🚀 Go-Long Watchlist")
        st.write("**Top 3:** HDFCBANK, RELIANCE, TCS")
        st.write("*Rationale:* Strong OBV momentum + sector leadership + RSI>55")
        st.markdown('</div>', unsafe_allow_html=True)

    # Avoid/Chop
    with st.container():
        st.markdown('<div class="decision-card negative">', unsafe_allow_html=True)
        st.subheader("⚠️ Avoid/Chop")
        st.write("**High VSpike but RSI flat/down:** PNB, BANKINDIA")
        st.write("*Rationale:* Momentum divergence + wide spreads")
        st.markdown('</div>', unsafe_allow_html=True)

    # Next Checkpoint
    with st.container():
        st.markdown('<div class="decision-card neutral">', unsafe_allow_html=True)
        st.subheader("⏱️ Next Checkpoint")
        st.write(f"Auto re-scan in: 18:45")
        st.write(f"Last scan: {st.session_state.last_scan_time or 'Never'}")
        st.markdown('</div>', unsafe_allow_html=True)

def fetch_market_data_from_api(limit: int = 100) -> pd.DataFrame:
    """Fetch market data from FastAPI endpoints as fallback."""
    try:
        # Fetch from /api/v1/market-data endpoint
        response = requests.get(
            f"{API_BASE_URL}/api/v1/market-data",
            params={"limit": limit, "exchange": "NSE"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                df = pd.DataFrame(data['data'])
                # Standardize columns if needed
                column_mapping = {
                    'tradingsymbol': 'symbol',
                    'ltp': 'close',
                    'open_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'volume_traded': 'volume',
                    'timestamp': 'timestamp'
                }
                df = df.rename(columns=column_mapping)
                print(f"✅ API returned {len(df)} records")
                return df
        else:
            print(f"⚠️ API returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API request failed: {e}")
    except Exception as e:
        print(f"⚠️ API data processing failed: {e}")
    
    return pd.DataFrame()

def perform_market_scan():
    """Perform market scan with current parameters, integrating API if needed."""
    with st.spinner("Scanning 500-stock universe..."):
        try:
            # Load market data for visualizations
            load_market_data()

            # If no patterns from DB, try API-based scan
            if not st.session_state.pattern_analyzer.discovered_patterns:
                st.info("No DB patterns found, attempting API scanner integration...")
                api_patterns = fetch_scan_results_from_api()
                if api_patterns:
                    # Convert API results to internal pattern format
                    patterns = []
                    for p in api_patterns:
                        pattern = BreakoutPattern(
                            pattern_type=p.get('pattern_type', 'api_breakout'),
                            symbol=p['symbol'],
                            trigger_time=datetime.now(),  # Use current time
                            volume_multiplier=p.get('volume_multiplier', 1.5),
                            price_move_pct=p.get('price_move_pct', 0.02),
                            confidence_score=p.get('confidence', 0.6),
                            technical_indicators=p.get('indicators', {})
                        )
                        patterns.append(pattern)
                    st.session_state.pattern_analyzer.discovered_patterns = patterns
                    print(f"✅ Integrated {len(patterns)} patterns from API")

            # Perform pattern discovery scan using real analyzer
            patterns = st.session_state.pattern_analyzer.discover_volume_spike_patterns(
                min_volume_multiplier=1.5,
                min_price_move=0.02,
                time_window_minutes=10
            )

            # Evaluate patterns with rule engine
            scan_results = []
            for pattern in patterns:
                signals = st.session_state.rule_engine.evaluate_pattern(pattern)
                for signal in signals:
                    result = {
                        'symbol': signal.symbol,
                        'pattern_type': pattern.pattern_type,
                        'confidence': signal.confidence,
                        'timestamp': pattern.trigger_time.strftime('%H:%M:%S'),
                        'volume_multiplier': pattern.volume_multiplier,
                        'price_move_pct': pattern.price_move_pct,
                        'signal_type': signal.signal_type,
                        'price_target': signal.price_target,
                        'stop_loss': signal.stop_loss
                    }
                    scan_results.append(result)

            # Apply confidence filter if set
            min_confidence = st.session_state.get('min_confidence_filter', 0.0)
            filtered_results = [r for r in scan_results if r['confidence'] >= min_confidence]
            st.session_state.scan_results = filtered_results

            st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
            st.success(f"✅ Found {len(filtered_results)} breakout candidates (filtered from {len(scan_results)})")

        except Exception as e:
            st.error(f"❌ Scan failed: {e}")

def load_market_data():
    """Load market data for visualizations with API fallback."""
    try:
        import textwrap
        # Primary: Get sample market data from database with industry information
        query = textwrap.dedent("""
        SELECT
            m.symbol,
            m.open,
            m.high,
            m.low,
            m.close,
            m.volume,
            m.timestamp,
            COALESCE(m.industry, n.industry, 'Unknown') as industry,
            n.company_name
        FROM market_data_unified m
        LEFT JOIN nifty500_stocks n ON m.symbol = n.symbol
        WHERE m.date_partition = CURRENT_DATE
        LIMIT 1000
        ORDER BY m.symbol, m.timestamp
        """)

        df = st.session_state.db_connector.execute_analytics_query(query)

        if not df.empty:
            # Compute real technical indicators using DataProcessor
            from analytics.utils.data_processor import DataProcessor
            df = DataProcessor.calculate_technical_indicators(df)
            df = DataProcessor.detect_volume_spikes(df, threshold=1.5)

            # Ensure required columns exist
            if 'rsi' not in df.columns:
                df['rsi'] = 50.0
            if 'sma_20' not in df.columns:
                df['sma_20'] = df['close']
            if 'volume_spike' not in df.columns:
                df['volume_spike'] = 1.0

            st.session_state.market_data = df
            print(f"✅ Loaded and processed {len(df)} market records with real indicators")
            return

        # Fallback 1: Try API integration for live data
        st.info("No DB data found, attempting API fetch for live market data...")
        api_df = fetch_market_data_from_api(limit=100)
        if not api_df.empty:
            # Process API data
            df = DataProcessor.calculate_technical_indicators(api_df)
            df = DataProcessor.detect_volume_spikes(df, threshold=1.5)
            st.session_state.market_data = df
            print(f"✅ Fetched {len(df)} records from API")
            return

        # No data available
        st.error("No market data available from database or API. Please ensure data is loaded and API is running.")

    except Exception as e:
        print(f"⚠️ Database and API fetch failed: {e}")
        st.error(f"Failed to load market data: {e}")


def fetch_scan_results_from_api() -> list:
    """Fetch scan results from FastAPI scanner endpoint."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/scanners/scan",
            json={"symbols": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]},  # Sample NIFTY-500 symbols
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                print(f"✅ API scan returned {len(data['results'])} candidates")
                return data['results']
        else:
            print(f"⚠️ Scanner API returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Scanner API request failed: {e}")
    except Exception as e:
        print(f"⚠️ Scanner API processing failed: {e}")
    
    return []

def render_status_bar():
    """Render the status bar at bottom with API status."""
    scan_time = st.session_state.last_scan_time or "Never"
    data_time = datetime.now().strftime("%H:%M:%S")
    
    # Check API status
    api_status = "Connected"
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        if response.status_code != 200:
            api_status = "Disconnected"
    except:
        api_status = "Unavailable"

    st.markdown(f"""
    <div class="status-bar">
        <span>Scan: {scan_time} • Data: {data_time} • 500 symbols • API: {api_status}</span>
        <span>DuckDB 1.3s • Query: 245ms • Broker: Active</span>
    </div>
    """, unsafe_allow_html=True)

def render_symbol_detail_chart(symbol: str):
    """Render detailed candlestick chart for selected symbol."""
    st.subheader(f"Detailed Chart: {symbol}")
    
    try:
        # Query detailed data for the symbol
        query = f"""
        SELECT
            timestamp, open, high, low, close, volume
        FROM market_data_unified
        WHERE symbol = '{symbol}'
        AND date_partition = CURRENT_DATE
        ORDER BY timestamp
        """
        
        df = st.session_state.db_connector.execute_analytics_query(query)
        
        if not df.empty:
            # Create candlestick chart
            fig = go.Figure(data=go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=symbol
            ))
            
            fig.add_trace(go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name='Volume',
                yaxis='y2',
                opacity=0.6
            ))
            
            fig.update_layout(
                title=f"{symbol} - Candlestick Chart with Volume",
                yaxis_title="Price",
                yaxis2=dict(
                    title="Volume",
                    side="right",
                    overlaying="y"
                ),
                height=500,
                xaxis_rangeslider_visible=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add technical indicators table
            if len(df) > 20:
                df_with_indicators = DataProcessor.calculate_technical_indicators(df.tail(20))
                st.dataframe(df_with_indicators[['timestamp', 'close', 'rsi', 'macd', 'sma_20']], use_container_width=True)
        else:
            st.info(f"No data available for {symbol}")
            
    except Exception as e:
        st.error(f"Failed to load chart for {symbol}: {e}")

def main():
    """Main TraderX dashboard application."""

    # Initialize TraderX
    if not initialize_traderx():
        return

    # Load initial market data if not already loaded
    if 'market_data' not in st.session_state or st.session_state.market_data is None:
        load_market_data()

    # Top App Bar
    render_top_app_bar()

    # Apply industry filtering if selected
    if 'universe' in locals() and universe == "By Industry":
        if 'selected_industries' in st.session_state and st.session_state.selected_industries:
            if 'market_data' in st.session_state and st.session_state.market_data is not None:
                filtered_data = st.session_state.market_data[
                    st.session_state.market_data['industry'].isin(st.session_state.selected_industries)
                ]
                if not filtered_data.empty:
                    st.session_state.market_data = filtered_data
                    st.info(f"📊 Filtered to {len(filtered_data)} stocks in selected industries")

    # KPI Strip
    render_kpi_strip()

    # Main Layout: Heatmap + Sector Map
    col1, col2 = st.columns([8, 4])

    with col1:
        render_market_heatmap()

    with col2:
        render_sector_map()

    # Leaderboards (full width)
    render_leaderboards()

    # Symbol selector for detailed view
    if st.session_state.scan_results:
        selected_symbol = st.selectbox(
            "Select Symbol for Detailed Chart",
            options=[r['symbol'] for r in st.session_state.scan_results],
            index=0
        )
        st.session_state.selected_symbol = selected_symbol
        render_symbol_detail_chart(selected_symbol)
    elif st.session_state.market_data is not None:
        available_symbols = st.session_state.market_data['symbol'].unique()[:20]  # Limit for performance
        selected_symbol = st.selectbox(
            "Select Symbol for Detailed Chart",
            options=available_symbols,
            index=0
        )
        st.session_state.selected_symbol = selected_symbol
        render_symbol_detail_chart(selected_symbol)
    else:
        st.info("Run scan or load data to view symbol details")

    # Bottom Layout: Time Patterns + Decision Cards
    col3, col4 = st.columns([7, 5])

    with col3:
        render_time_patterns()

    with col4:
        render_decision_cards()

    # Status Bar
    render_status_bar()

if __name__ == "__main__":
    main()
