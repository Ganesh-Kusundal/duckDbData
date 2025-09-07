// Mock data for dashboard components
import { ScannerType, BreakoutStatus, TimeRange } from '../types/enums';

// Data for global state store
export const mockStore = {
  selectedTimeRange: TimeRange.LAST_30_DAYS as const,
  selectedScannerType: ScannerType.ENHANCED_BREAKOUT as const,
  isLoading: false,
  lastUpdated: new Date('2025-01-15T10:30:00Z')
};

// Data returned by API queries
export const mockQuery = {
  performanceSummary: {
    totalScans: 45,
    successfulBreakouts: 86,
    failedBreakouts: 41,
    successRate: 67.7,
    avgPriceChange: 2.34,
    avgExecutionTime: 2340,
    avgProbabilityScore: 75.2
  },
  dailyPerformance: [
    { date: new Date('2025-01-08'), successful: 8, failed: 3, successRate: 72.7 },
    { date: new Date('2025-01-09'), successful: 6, failed: 5, successRate: 54.5 },
    { date: new Date('2025-01-10'), successful: 12, failed: 2, successRate: 85.7 },
    { date: new Date('2025-01-11'), successful: 9, failed: 4, successRate: 69.2 },
    { date: new Date('2025-01-12'), successful: 7, failed: 6, successRate: 53.8 },
    { date: new Date('2025-01-13'), successful: 11, failed: 3, successRate: 78.6 },
    { date: new Date('2025-01-14'), successful: 10, failed: 5, successRate: 66.7 },
    { date: new Date('2025-01-15'), successful: 13, failed: 2, successRate: 86.7 }
  ],
  topPerformers: [
    {
      symbol: "RELIANCE" as const,
      probabilityScore: 89.5,
      priceChange: 3.2,
      volumeRatio: 2.8,
      breakoutPrice: 2450.50,
      eodPrice: 2528.34,
      status: BreakoutStatus.SUCCESSFUL as const
    },
    {
      symbol: "TCS" as const,
      probabilityScore: 87.2,
      priceChange: 2.9,
      volumeRatio: 2.1,
      breakoutPrice: 3890.25,
      eodPrice: 4003.12,
      status: BreakoutStatus.SUCCESSFUL as const
    },
    {
      symbol: "HDFCBANK" as const,
      probabilityScore: 84.8,
      priceChange: 2.1,
      volumeRatio: 1.9,
      breakoutPrice: 1678.90,
      eodPrice: 1714.15,
      status: BreakoutStatus.SUCCESSFUL as const
    }
  ],
  priceChangeDistribution: [
    { range: "-5 to -3", count: 2 },
    { range: "-3 to -1", count: 8 },
    { range: "-1 to 0", count: 31 },
    { range: "0 to 1", count: 45 },
    { range: "1 to 3", count: 28 },
    { range: "3 to 5", count: 12 },
    { range: "5+", count: 1 }
  ],
  volumePriceData: [
    { volume: 125000, priceChange: 2.1, symbol: "RELIANCE" as const },
    { volume: 89000, priceChange: 1.8, symbol: "TCS" as const },
    { volume: 156000, priceChange: 3.2, symbol: "HDFCBANK" as const },
    { volume: 67000, priceChange: -0.5, symbol: "INFY" as const },
    { volume: 98000, priceChange: 1.2, symbol: "WIPRO" as const },
    { volume: 234000, priceChange: 4.1, symbol: "ADANIPORTS" as const },
    { volume: 45000, priceChange: -1.2, symbol: "BAJFINANCE" as const },
    { volume: 178000, priceChange: 2.8, symbol: "MARUTI" as const }
  ]
};

// Data passed as props to the root component
export const mockRootProps = {
  title: "Enhanced Breakout Scanner Dashboard" as const,
  subtitle: "Top 3 Stocks Per Day" as const,
  refreshInterval: 30000,
  maxResults: 10,
  minProbabilityScore: 15.0
};