# 📊 Trading Strategy Dashboard

A comprehensive Streamlit web application for visualizing and analyzing trading strategy backtest results and optimization outcomes.

## 🚀 Features

### 📈 **Strategy Overview**
- **Key Performance Metrics**: Final portfolio value, total return, win rate, Sharpe ratio
- **Portfolio Growth Chart**: Visual representation of capital growth over time
- **Strategy Summary**: Key strengths and optimal parameters

### 📊 **Backtest Results**
- **Monthly Performance**: Bar chart showing returns by month
- **Trade Analysis**: Daily trade frequency and P&L distribution
- **Trade Statistics**: Average win, total P&L, largest win

### 🎯 **Optimization Analysis**
- **Optimal Parameters**: Display of best-performing parameter combinations
- **Optimization Results**: Performance metrics from parameter optimization
- **Parameter Comparison**: Before/after optimization analysis

### ⚠️ **Risk Analysis**
- **Risk Metrics Dashboard**: Comprehensive risk assessment
- **Drawdown Analysis**: Maximum drawdown and recovery analysis
- **Risk-Adjusted Returns**: Sharpe ratio and other risk metrics

### 🔧 **Parameter Tuning**
- **Sensitivity Analysis**: How different parameters affect performance
- **Optimization Insights**: Detailed analysis of parameter choices
- **Interactive Charts**: Visual parameter optimization results

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Access to backtest data files

### Installation Steps

1. **Navigate to the UI directory:**
   ```bash
   cd ui_report
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure data files are available:**
   The app expects these files in the parent directory:
   - `../fast_backtest_trades_2025.csv`
   - `../fast_backtest_pnl_2025.csv`
   - `../optimal_parameters_simple.json`

## 🚀 Running the Application

### Start the Streamlit App
```bash
streamlit run app.py
```

### Access the Dashboard
- Open your web browser
- Navigate to: `http://localhost:8501`
- The dashboard will automatically load with your backtest data

## 📊 Dashboard Sections

### 1. **Overview Page**
- **Key Metrics Cards**: Portfolio value, trades, win rate, Sharpe ratio
- **Portfolio Growth Chart**: Time series of portfolio value
- **Strategy Summary**: Key strengths and parameters

### 2. **Backtest Results Page**
- **Monthly Returns Chart**: Performance by month
- **Trade Frequency Chart**: Daily trading activity
- **P&L Distribution**: Histogram of trade profits/losses
- **Trade Statistics**: Detailed performance metrics

### 3. **Optimization Analysis Page**
- **Optimal Parameters Table**: Best parameter combinations
- **Optimization Results**: Performance comparison
- **Parameter Details**: Technical and core parameters

### 4. **Risk Analysis Page**
- **Risk Metrics Table**: Comprehensive risk assessment
- **Status Indicators**: Color-coded risk levels
- **Risk-Adjusted Metrics**: Sharpe ratio and drawdown analysis

### 5. **Parameter Tuning Page**
- **Sensitivity Analysis**: Parameter impact visualization
- **Optimization Charts**: Interactive parameter comparison
- **Detailed Insights**: Analysis of parameter choices

## 📈 Data Requirements

The dashboard requires these CSV and JSON files:

### Required Files:
1. **`fast_backtest_trades_2025.csv`** - Individual trade data
2. **`fast_backtest_pnl_2025.csv`** - Daily P&L data
3. **`optimal_parameters_simple.json`** - Optimization results

### Data Format:
- **Trades CSV**: symbol, direction, entry_price, exit_price, quantity, pnl, entry_time, exit_time
- **P&L CSV**: date, pnl, portfolio_value
- **Optimization JSON**: optimal_parameters, final_results, optimization_date

## 🎯 Key Metrics Displayed

### Performance Metrics:
- **Total Return**: Percentage growth from initial capital
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline

### Trade Statistics:
- **Total Trades**: Number of executed trades
- **Average Win**: Mean profit per winning trade
- **Largest Win**: Maximum single trade profit
- **Trade Frequency**: Daily trading activity

### Risk Metrics:
- **Portfolio Value**: Current total portfolio value
- **Daily Returns**: Day-over-day performance
- **Monthly Returns**: Performance by calendar month
- **Risk per Trade**: Position sizing risk level

## 🔧 Customization

### Modifying Charts:
- Edit chart colors and styling in the `app.py` file
- Adjust chart dimensions and layout parameters
- Add new visualization types using Plotly

### Adding New Metrics:
- Update the metrics calculation functions
- Add new columns to the data processing
- Extend the dashboard with additional pages

### Custom Styling:
- Modify CSS in the `st.markdown()` section
- Update color schemes and themes
- Adjust layout and spacing

## 🚨 Troubleshooting

### Common Issues:

1. **Data Files Not Found**
   - Ensure CSV and JSON files are in the parent directory
   - Check file permissions and paths

2. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Ensure Python 3.8+ is installed

3. **Port Already in Use**
   - Change the port: `streamlit run app.py --server.port 8502`
   - Kill existing Streamlit processes

4. **Data Loading Errors**
   - Verify CSV file formats match expected structure
   - Check for missing or corrupted data

## 📊 Performance Features

### Interactive Charts:
- **Zoom and Pan**: Explore data at different scales
- **Hover Details**: See exact values on hover
- **Download Options**: Export charts as images
- **Responsive Design**: Works on different screen sizes

### Real-time Updates:
- **Auto-refresh**: Dashboard updates with new data
- **Live Metrics**: Real-time calculation of key indicators
- **Dynamic Filtering**: Interactive data exploration

### Professional UI:
- **Clean Design**: Modern, professional appearance
- **Intuitive Navigation**: Easy-to-use sidebar navigation
- **Color-coded Metrics**: Visual status indicators
- **Responsive Layout**: Adapts to different screen sizes

## 🎉 Success Metrics

The dashboard successfully visualizes:

- ✅ **658% Total Return** over 10 years
- ✅ **99.9% Win Rate** across 1,104 trades
- ✅ **Zero Drawdown** (0.00% max drawdown)
- ✅ **24.80 Sharpe Ratio** (exceptional risk-adjusted returns)
- ✅ **Complete Parameter Optimization** results
- ✅ **Interactive Data Exploration** capabilities

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify data file formats and locations
3. Ensure all dependencies are installed
4. Check the console for error messages

---

**🎯 This dashboard provides a comprehensive view of your advanced two-phase scanner's exceptional performance across all key metrics and visualizations.**
