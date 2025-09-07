import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';
import { styled } from '@mui/material/styles';
import ShowChartOutlinedIcon from '@mui/icons-material/ShowChartOutlined';
import { DailyPerformanceData } from '../types/schema';
import { formatDate, formatPercentage } from '../utils/formatters';

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

interface DailyPerformanceChartProps {
  data: DailyPerformanceData[];
}

const DailyPerformanceChart: React.FC<DailyPerformanceChartProps> = ({ data }) => {
  const chartData = data.map(item => ({
    date: formatDate(item.date),
    successful: item.successful,
    failed: item.failed,
    successRate: item.successRate
  }));

  const xAxisData = chartData.map(item => item.date);
  const successfulData = chartData.map(item => item.successful);
  const failedData = chartData.map(item => item.failed);
  const successRateData = chartData.map(item => item.successRate);

  return (
    <ChartContainer>
      <ChartHeader>
        <ShowChartOutlinedIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h3" component="h2">
          Daily Performance
        </Typography>
      </ChartHeader>
      
      <Box sx={{ height: 300, width: '100%' }}>
        <LineChart
          xAxis={[{
            scaleType: 'point',
            data: xAxisData,
            tickLabelStyle: {
              fontSize: 12,
              fill: '#6c757d'
            }
          }]}
          yAxis={[
            {
              id: 'count',
              scaleType: 'linear',
              tickLabelStyle: {
                fontSize: 12,
                fill: '#6c757d'
              }
            },
            {
              id: 'percentage',
              scaleType: 'linear',
              tickLabelStyle: {
                fontSize: 12,
                fill: '#6c757d'
              }
            }
          ]}
          series={[
            {
              id: 'successful',
              label: 'Successful',
              data: successfulData,
              color: '#28a745',
              yAxisId: 'count',
              curve: 'monotoneX',
              showMark: true
            },
            {
              id: 'failed',
              label: 'Failed',
              data: failedData,
              color: '#dc3545',
              yAxisId: 'count',
              curve: 'monotoneX',
              showMark: true
            },
            {
              id: 'successRate',
              label: 'Success Rate (%)',
              data: successRateData,
              color: '#667eea',
              yAxisId: 'percentage',
              curve: 'monotoneX',
              showMark: true
            }
          ]}
          width={undefined}
          height={300}
          margin={{ left: 60, right: 60, top: 20, bottom: 60 }}
          grid={{ horizontal: true, vertical: true }}
          tooltip={{
            formatter: (params) => {
              const { dataIndex, seriesId } = params;
              const item = chartData[dataIndex];
              if (seriesId === 'successRate') {
                return `${formatPercentage(item.successRate)}`;
              }
              return `${params.value}`;
            }
          }}
          skipAnimation={false}
        />
      </Box>
    </ChartContainer>
  );
};

export default DailyPerformanceChart;