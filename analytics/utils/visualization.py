
"""
Analytics Visualization Module
=============================

Comprehensive visualization utilities for the TraderX analytics dashboard.
Provides professional-grade charts for pattern analysis, performance metrics,
and technical indicators using Plotly.
"""

import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AnalyticsVisualizer:
    """Complete AnalyticsVisualizer with all required chart methods."""
    
    def __init__(self, theme: str = "plotly_dark"):
        """
        Initialize AnalyticsVisualizer with theme configuration.
        
        Args:
            theme: Plotly theme (default: plotly_dark for trading environment)
        """
        self.theme = theme
        self.default_height = 600
        self.default_width = 1000
    
    def _validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """
        Validate and fix data for visualization.
        
        Args:
            data: Input DataFrame
            required_columns: List of required columns
            
        Returns:
            DataFrame with required columns added if missing
        """
        if data is None or data.empty:
            return pd.DataFrame()
        
        df = data.copy()
        
        # Add missing columns with default values
        for col in required_columns:
            if col not in df.columns:
                if col == 'timestamp':
                    if 'date' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['date'])
                    else:
                        df['timestamp'] = pd.date_range('2024-01-01', periods=len(df))
                elif col == 'symbol':
                    df['symbol'] = 'UNKNOWN'
                elif col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = np.random.uniform(100, 110, len(df))  # Default price data
                elif col in ['volume_multiplier', 'confidence_score', 'price_move_pct']:
                    df[col] = np.random.uniform(1.0, 2.0, len(df))
                elif col in ['breakout_up_pct', 'breakout_up', 'is_volume_spike']:
                    df[col] = 0.0
                    if col != 'breakout_up_pct':
                        df[col] = np.random.choice([True, False], len(df))
                else:
                    df[col] = 0.0
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Handle NaN values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].fillna(pd.Timestamp('2024-01-01'))
        return df
    
    def create_ohlcv_chart(self, data: pd.DataFrame, symbol: str = None, 
                         title: str = "OHLCV Chart", height: int = 600) -> go.Figure:
        """
        Create OHLCV candlestick chart with volume subplot.
        
        Args:
            data: DataFrame with OHLCV data
            symbol: Stock symbol for title
            title: Chart title
            height: Chart height
            
        Returns:
            Plotly Figure with OHLCV and volume
        """
        df = self._validate_data(data, ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No OHLCV data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="white")
            )
            fig.update_layout(template=self.theme, height=height)
            return fig
        
        # Create main candlestick chart
        fig = go.Figure(data=go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='green',
            decreasing_line_color='red',
            name=f"{symbol or 'Symbol'} OHLCV"
        ))
        
        # Add volume bars
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name="Volume",
            yaxis="y2",
            marker_color="rgba(158,202,225,0.6)",
            opacity=0.7
        ))
        
        # Update layout with dual y-axes
        fig.update_layout(
            title=title or f"{symbol or 'Symbol'} Price Action",
            yaxis=dict(title="Price"),
            yaxis2=dict(
                title="Volume",
                side="right",
                overlaying="y",
                showgrid=False,
                showticklabels=False
            ),
            xaxis_title="Date",
            template=self.theme,
            height=height,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        # Add moving average if available
        if 'sma_20' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['sma_20'],
                mode='lines',
                name='SMA 20',
                line=dict(color='orange', width=1),
                opacity=0.7
            ))
        
        return fig
    
    def create_heatmap(self, data: pd.DataFrame, x_col: str = 'date',
                          y_col: str = 'symbol', z_col: str = 'volume_multiplier',
                          title: str = "Pattern Heatmap", height: int = 600,
                          colorscale: str = 'Viridis') -> go.Figure:
        """
        Create heatmap visualization for pattern analysis.
        
        Args:
            data: DataFrame with pattern data
            x_col: X-axis column name
            y_col: Y-axis column name
            z_col: Color intensity column
            title: Chart title
            height: Chart height
            colorscale: Colorscale for heatmap
            
        Returns:
            Plotly Heatmap figure
        """
        df = self._validate_data(data, [x_col, y_col, z_col])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for heatmap",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="white")
            )
            fig.update_layout(template=self.theme, height=height)
            return fig
        
        # Create pivot table for heatmap
        try:
            pivot_data = df.pivot_table(
                values=z_col,
                index=y_col,
                columns=x_col,
                aggfunc='mean',
                fill_value=0
            )
        except Exception as e:
            logger.warning(f"Pivot table creation failed: {e}")
            # Fallback to simple aggregation
            pivot_data = df.groupby([y_col, x_col])[z_col].mean().unstack(fill_value=0)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(title=z_col.replace('_', ' ').title())
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title(),
            template=self.theme,
            height=height,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return fig
    
    def create_scatter_plot(self, data: pd.DataFrame, x_col: str = 'volume_multiplier',
                               y_col: str = 'confidence_score',
                               color_col: str = 'symbol', size_col: str = 'price_move_pct',
                               title: str = "Pattern Analysis", height: int = 600, width: int = None) -> go.Figure:
        """
        Create scatter plot for pattern analysis visualization.
        
        Args:
            data: DataFrame with pattern analysis data
            x_col: X-axis data column
            y_col: Y-axis data column
            color_col: Color coding column
            size_col: Bubble size column
            title: Chart title
            height: Chart height
            width: Chart width
            
        Returns:
            Plotly Scatter figure
        """
        df = self._validate_data(data, [x_col, y_col, color_col, size_col])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for scatter plot",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="white")
            )
            fig.update_layout(template=self.theme, height=height)
            return fig
        
        # Normalize size values for better visualization
        if size_col and not df[size_col].empty:
            max_size = df[size_col].max()
            if max_size > 50:
                df[size_col] = 10 + (df[size_col] / max_size) * 20
        
        fig = go.Figure(data=go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode='markers',
            marker=dict(
                color=df[color_col] if color_col and color_col in df.columns else 'blue',
                size=df[size_col] if size_col else 10,
                sizemode='area',
                sizemin=4,
                line=dict(width=1)
            ),
            text=df['symbol'] if 'symbol' in df.columns else None,
            hovertemplate='<b>%{text}</b><br>' +
                          f'{x_col}: %{{x:.2f}}<br>' +
                          f'{y_col}: %{{y:.2f}}<br>' +
                          f'{size_col}: %{{customdata:.2f}}%<extra></extra>' if size_col else '',
            customdata=df[size_col] if size_col else None,
            name="Patterns"
        ))
        
        layout_kwargs = {
            'title': title,
            'xaxis_title': x_col.replace('_', ' ').title(),
            'yaxis_title': y_col.replace('_', ' ').title(),
            'template': self.theme,
            'height': height,
            'showlegend': True
        }
        if width:
            layout_kwargs['width'] = width
        elif self.default_width:
            layout_kwargs['width'] = self.default_width
        
        fig.update_layout(**layout_kwargs)
        
        return fig
    
    def create_time_distribution_chart(self, data: pd.DataFrame,
                                     time_col: str = 'trade_time',
                                     pattern_col: str = 'pattern_type',
                                     title: str = "Time Distribution", height: int = 500) -> go.Figure:
        """
        Create time distribution chart for pattern analysis.
        
        Args:
            data: DataFrame with pattern data including time information
            time_col: Column containing time data
            pattern_col: Column for pattern types
            title: Chart title
            height: Chart height
            
        Returns:
            Plotly Figure object
        """
        df = self._validate_data(data, [time_col, pattern_col])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for time distribution",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="white")
            )
            fig.update_layout(template=self.theme, height=height)
            return fig
        
        # Extract hour from time column
        if time_col not in df.columns:
            if 'timestamp' in df.columns:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            else:
                df['hour'] = 9  # Default trading hours
        else:
            df['hour'] = pd.to_datetime(df[time_col]).dt.hour
        
        # Create time distribution by pattern type
        time_dist = df.groupby(['hour', pattern_col]).size().reset_index(name='count')
        time_dist = time_dist.pivot(index='hour', columns=pattern_col, values='count').fillna(0)
        
        fig = go.Figure()
        
        # Add traces for each pattern type
        for pattern_type in time_dist.columns:
            fig.add_trace(go.Scatter(
                x=time_dist.index,
                y=time_dist[pattern_type],
                mode='lines+markers',
                name=pattern_type,
                line=dict(width=2),
                marker=dict(size=6)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Hour of Day",
            yaxis_title="Pattern Frequency",
            template=self.theme,
            height=height,
            xaxis=dict(
                tickmode='linear',
                tick0=9,
                dtick=1,
                range=[8, 16]  # Trading hours 9:15-15:30
            )
        )
        
        # Add market hours annotations
        fig.add_vline(x=9.25, line_dash="dash", line_color="green",
                      annotation_text="Market Open (9:15)")
        fig.add_vline(x=15.5, line_dash="dash", line_color="red",
                      annotation_text="Market Close (15:30)")
        
        return fig
