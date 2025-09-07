import React from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { PieChart } from '@mui/x-charts/PieChart';
import { styled } from '@mui/material/styles';
import PieChartOutlinedIcon from '@mui/icons-material/PieChartOutlined';
import { PerformanceSummary } from '../types/schema';

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

interface SuccessDistributionChartProps {
  data: PerformanceSummary;
}

const SuccessDistributionChart: React.FC<SuccessDistributionChartProps> = ({ data }) => {
  const pieData = [
    {
      id: 'successful',
      label: 'Successful Breakouts',
      value: data.successfulBreakouts,
      color: '#28a745'
    },
    {
      id: 'failed',
      label: 'Failed Breakouts',
      value: data.failedBreakouts,
      color: '#dc3545'
    }
  ];

  return (
    <ChartContainer>
      <ChartHeader>
        <PieChartOutlinedIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h3" component="h2">
          Success Distribution
        </Typography>
      </ChartHeader>
      
      <Box sx={{ height: 300, width: '100%', display: 'flex', justifyContent: 'center' }}>
        <PieChart
          series={[{
            data: pieData,
            highlightScope: { fade: 'global', highlight: 'item' },
            faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
            innerRadius: 40,
            outerRadius: 120,
            paddingAngle: 2,
            cornerRadius: 8,
            arcLabel: (item) => `${item.value}`,
            arcLabelMinAngle: 35,
            valueFormatter: (item) => `${item.value} (${((item.value / (data.successfulBreakouts + data.failedBreakouts)) * 100).toFixed(1)}%)`
          }]}
          width={400}
          height={300}
          margin={{ top: 20, bottom: 20, left: 20, right: 20 }}
          tooltip={{
            formatter: (params) => {
              const percentage = ((params.value / (data.successfulBreakouts + data.failedBreakouts)) * 100).toFixed(1);
              return `${params.label}: ${params.value} (${percentage}%)`;
            }
          }}
          skipAnimation={false}
        />
      </Box>
    </ChartContainer>
  );
};

export default SuccessDistributionChart;