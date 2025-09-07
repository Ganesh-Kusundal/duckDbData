import React from 'react';
import { Card, CardContent, Typography, Stack, Box, Chip } from '@mui/material';
import { styled } from '@mui/material/styles';
import { PerformanceSummary } from '../types/schema';
import { formatPercentage, formatNumber, formatExecutionTime } from '../utils/formatters';

const SummaryCard = styled(Card)(({ theme }) => ({
  height: '100%',
  background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.grey[50]} 100%)`,
  border: `1px solid ${theme.palette.grey[200]}`,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
  transition: 'all 0.3s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[8]
  }
}));

const MetricBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.grey[200]}`,
  textAlign: 'center',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    backgroundColor: theme.palette.grey[50],
    transform: 'scale(1.02)'
  }
}));

const MetricValue = styled(Typography)(({ theme }) => ({
  fontSize: '2rem',
  fontWeight: 700,
  color: theme.palette.primary.main,
  marginBottom: theme.spacing(0.5)
}));

const MetricLabel = styled(Typography)(({ theme }) => ({
  fontSize: '0.875rem',
  color: theme.palette.text.secondary,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  fontWeight: 500
}));

interface PerformanceSummaryCardProps {
  data: PerformanceSummary;
}

const PerformanceSummaryCard: React.FC<PerformanceSummaryCardProps> = ({ data }) => {
  const getSuccessRateColor = (rate: number) => {
    if (rate >= 70) return 'success';
    if (rate >= 50) return 'warning';
    return 'error';
  };

  return (
    <SummaryCard>
      <CardContent sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h3" component="h2" color="text.primary">
              Performance Summary
            </Typography>
            <Chip 
              label={`${formatPercentage(data.successRate)} Success Rate`}
              color={getSuccessRateColor(data.successRate)}
              variant="filled"
              sx={{ fontWeight: 600 }}
            />
          </Box>
          
          <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 2 }}>
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2">
                {formatNumber(data.totalScans)}
              </MetricValue>
              <MetricLabel>Total Scans</MetricLabel>
            </MetricBox>
            
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2" sx={{ color: 'success.main' }}>
                {formatNumber(data.successfulBreakouts)}
              </MetricValue>
              <MetricLabel>Successful</MetricLabel>
            </MetricBox>
            
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2" sx={{ color: 'error.main' }}>
                {formatNumber(data.failedBreakouts)}
              </MetricValue>
              <MetricLabel>Failed</MetricLabel>
            </MetricBox>
          </Stack>
          
          <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 2 }}>
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2" sx={{ color: 'info.main' }}>
                {formatPercentage(data.avgPriceChange)}
              </MetricValue>
              <MetricLabel>Avg Price Change</MetricLabel>
            </MetricBox>
            
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2" sx={{ color: 'secondary.main' }}>
                {data.avgProbabilityScore.toFixed(1)}
              </MetricValue>
              <MetricLabel>Avg Probability</MetricLabel>
            </MetricBox>
            
            <MetricBox sx={{ flex: 1, minWidth: 120 }}>
              <MetricValue variant="h2" sx={{ color: 'warning.main' }}>
                {formatExecutionTime(data.avgExecutionTime)}
              </MetricValue>
              <MetricLabel>Avg Execution</MetricLabel>
            </MetricBox>
          </Stack>
        </Stack>
      </CardContent>
    </SummaryCard>
  );
};

export default PerformanceSummaryCard;