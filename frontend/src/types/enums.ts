// Enums for scanner dashboard functionality
export enum ScannerType {
  ENHANCED_BREAKOUT = "enhanced_breakout",
  BASIC_BREAKOUT = "breakout", 
  VOLUME_SPIKE = "volume_spike",
  TECHNICAL = "technical"
}

export enum TimeRange {
  LAST_7_DAYS = "7d",
  LAST_30_DAYS = "30d", 
  CUSTOM = "custom"
}

export enum ChartType {
  LINE = "line",
  BAR = "bar",
  PIE = "pie",
  SCATTER = "scatter",
  HISTOGRAM = "histogram"
}

export enum BreakoutStatus {
  SUCCESSFUL = "successful",
  FAILED = "failed",
  PENDING = "pending"
}