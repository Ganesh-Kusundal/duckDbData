// String formatting functions for dashboard data
export const formatPercentage = (value: number): string => {
  return `${value.toFixed(2)}%`;
};

export const formatCurrency = (value: number): string => {
  return `₹${value.toFixed(2)}`;
};

export const formatNumber = (value: number): string => {
  return value.toLocaleString();
};

export const formatDate = (date: Date): string => {
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit'
  });
};

export const formatExecutionTime = (ms: number): string => {
  return `${ms}ms`;
};

export const formatVolumeRatio = (ratio: number): string => {
  return `${ratio.toFixed(1)}x`;
};

export const formatProbabilityScore = (score: number): string => {
  return score.toFixed(1);
};