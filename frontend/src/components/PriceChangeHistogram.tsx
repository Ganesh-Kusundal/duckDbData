import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { styled } from '@mui/material/styles';
import { PriceDistributionData } from '../types/schema';

const ChartContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  height: 400,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.grey[200]}`
}));

const ChartHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: theme.spacing(2),
  paddingBottom: theme.spacing(1),
  borderBottom: `1px solid ${theme.palette.grey[200]}`
}));

interface PriceChangeHistogramProps {
  data: PriceDistributionData[];
}

const PriceChangeHistogram: React.FC<PriceChangeHistogramProps> = ({ data }) => {
  const xAxisData = data.map(item => item.range);
  const seriesData = data.map(item => item.count);
  
  // Color bars based on price change ranges
  const getBarColor = (range: string) => {
    if (range.includes('-')) return '#dc3545'; // Red for negative
    if (range === '0 to 1') return '#ffc107'; // Yellow for small positive
    return '#28a745'; // Green for positive
  };

  return (
    <ChartContainer>
      <ChartHeader>
        <Typography variant="h3" component="h2">
          Price Change Distribution
        </Typography>
      </ChartHeader>
      
      <Box sx={{ height: 300, width: '100%' }}>
        <BarChart
          xAxis={[{
            scaleType: 'band',
            data: xAxisData,
            tickLabelStyle: {
              fontSize: 12,
              fill: '#6c757d',
              angle: -45
            }
          }]}
          yAxis={[{
            scaleType: 'linear',
            tickLabelStyle: {
              fontSize: 12,
              fill: '#6c757d'
            }
          }]}
          series={[{
            id: 'priceChange',
            label: 'Number of Stocks',
            data: seriesData,
            color: '#667eea'
          }]}
          width={undefined}
          height={300}
          margin={{ left: 60, right: 20, top: 20, bottom: 80 }}
          grid={{ horizontal: true }}
          tooltip={{
            formatter: (params) => {
              const range = xAxisData[params.dataIndex];
              return `${range}%: ${params.value} stocks`;
            }
          }}
          skipAnimation={false}
          borderRadius={4}
        />
      </Box>
    </ChartContainer>
  );
};

export default PriceChangeHistogram;