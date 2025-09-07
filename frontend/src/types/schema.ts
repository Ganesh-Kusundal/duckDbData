// Type definitions for dashboard data structures

// Props types (data passed to components)
export interface DashboardProps {
  title: string;
  subtitle: string;
  refreshInterval: number;
  maxResults: number;
  minProbabilityScore: number;
}

export interface PerformanceSummary {
  totalScans: number;
  successfulBreakouts: number;
  failedBreakouts: number;
  successRate: number;
  avgPriceChange: number;
  avgExecutionTime: number;
  avgProbabilityScore: number;
}

export interface DailyPerformanceData {
  date: Date;
  successful: number;
  failed: number;
  successRate: number;
}

export interface TopPerformer {
  symbol: string;
  probabilityScore: number;
  priceChange: number;
  volumeRatio: number;
  breakoutPrice: number;
  eodPrice: number;
  status: string;
}

export interface PriceDistributionData {
  range: string;
  count: number;
}

export interface VolumePriceData {
  volume: number;
  priceChange: number;
  symbol: string;
}

// Store types (global state data)
export interface DashboardStore {
  selectedTimeRange: string;
  selectedScannerType: string;
  isLoading: boolean;
  lastUpdated: Date;
}

// Query types (API response data)
export interface ScannerQueryResponse {
  performanceSummary: PerformanceSummary;
  dailyPerformance: DailyPerformanceData[];
  topPerformers: TopPerformer[];
  priceChangeDistribution: PriceDistributionData[];
  volumePriceData: VolumePriceData[];
}