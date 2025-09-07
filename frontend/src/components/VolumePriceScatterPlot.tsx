import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { ScatterChart } from '@mui/x-charts/ScatterChart';
import { styled } from '@mui/material/styles';
import { VolumePriceData } from '../types/schema';
import { formatNumber, formatPercentage } from '../utils/formatters';

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

interface VolumePriceScatterPlotProps {
  data: VolumePriceData[];
}

const VolumePriceScatterPlot: React.FC<VolumePriceScatterPlotProps> = ({ data }) => {
  const scatterData = data.map(item => ({
    x: item.volume,
    y: item.priceChange,
    id: item.symbol
  }));

  return (
    <ChartContainer>
      <ChartHeader>
        <Typography variant="h3" component="h2">
          Volume vs Price Change
        </Typography>
      </ChartHeader>
      
      <Box sx={{ height: 300, width: '100%' }}>
        <ScatterChart
          xAxis={[{
            id: 'volume',
            label: 'Volume',
            scaleType: 'linear',
            tickLabelStyle: {
              fontSize: 12,
              fill: '#6c757d'
            },
            valueFormatter: (value) => formatNumber(value)
          }]}
          yAxis={[{
            id: 'priceChange',
            label: 'Price Change (%)',
            scaleType: 'linear',
            tickLabelStyle: {
              fontSize: 12,
              fill: '#6c757d'
            },
            valueFormatter: (value) => formatPercentage(value)
          }]}
          series={[{
            id: 'volumePrice',
            label: 'Stocks',
            data: scatterData,
            color: '#667eea',
            markerSize: (dataIndex) => {
              // Vary marker size based on price change magnitude
              const priceChange = Math.abs(data[dataIndex].priceChange);
              return Math.max(6, Math.min(20, priceChange * 3));
            }
          }]}
          width={undefined}
          height={300}
          margin={{ left: 80, right: 20, top: 20, bottom: 60 }}
          grid={{ horizontal: true, vertical: true }}
          tooltip={{
            formatter: (params) => {
              const item = data[params.dataIndex];
              return `${item.symbol}: Volume ${formatNumber(item.volume)}, Price Change ${formatPercentage(item.priceChange)}`;
            }
          }}
          skipAnimation={false}
        />
      </Box>
    </ChartContainer>
  );
};

export default VolumePriceScatterPlot;