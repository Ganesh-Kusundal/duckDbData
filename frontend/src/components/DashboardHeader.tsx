import React from 'react';
import { Paper, Typography, Stack, Box } from '@mui/material';
import { styled } from '@mui/material/styles';
import BentoOutlinedIcon from '@mui/icons-material/BentoOutlined';

const HeaderContainer = styled(Paper)(({ theme }) => ({
  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
  color: theme.palette.common.white,
  padding: theme.spacing(4),
  marginBottom: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[4]
}));

const IconContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 60,
  height: 60,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: 'rgba(255, 255, 255, 0.2)',
  marginRight: theme.spacing(2)
}));

interface DashboardHeaderProps {
  title: string;
  subtitle: string;
}

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ title, subtitle }) => {
  return (
    <HeaderContainer elevation={0}>
      <Stack direction="row" alignItems="center">
        <IconContainer>
          <BentoOutlinedIcon sx={{ fontSize: 32, color: 'white' }} />
        </IconContainer>
        <Box>
          <Typography variant="h1" component="h1" sx={{ mb: 1 }}>
            📈 {title}
          </Typography>
          <Typography variant="h4" component="h2" sx={{ opacity: 0.9, fontWeight: 400 }}>
            {subtitle}
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.8, mt: 1 }}>
            Interactive visualization dashboard for breakout scanner performance analysis with plotly grid layout.
          </Typography>
        </Box>
      </Stack>
    </HeaderContainer>
  );
};

export default DashboardHeader;