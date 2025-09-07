import React from 'react';
import { 
  Paper, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Box, 
  Chip,
  Avatar
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { TopPerformer } from '../types/schema';
import { formatCurrency, formatPercentage, formatVolumeRatio, formatProbabilityScore } from '../utils/formatters';

const ListContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.grey[200]}`
}));

const ListHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: theme.spacing(2),
  paddingBottom: theme.spacing(1),
  borderBottom: `1px solid ${theme.palette.grey[200]}`
}));

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  fontWeight: 600,
  backgroundColor: theme.palette.grey[50],
  borderBottom: `2px solid ${theme.palette.grey[200]}`
}));

const SymbolCell = styled(TableCell)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  fontWeight: 600,
  color: theme.palette.text.primary
}));

interface TopPerformersListProps {
  data: TopPerformer[];
}

const TopPerformersList: React.FC<TopPerformersListProps> = ({ data }) => {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'successful': return 'success';
      case 'failed': return 'error';
      default: return 'warning';
    }
  };

  const getProbabilityColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getPriceChangeColor = (change: number) => {
    return change >= 0 ? 'success' : 'error';
  };

  return (
    <ListContainer>
      <ListHeader>
        <Typography variant="h3" component="h2">
          Top Performers
        </Typography>
      </ListHeader>
      
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <StyledTableCell>Symbol</StyledTableCell>
              <StyledTableCell align="right">Probability Score</StyledTableCell>
              <StyledTableCell align="right">Price Change</StyledTableCell>
              <StyledTableCell align="right">Volume Ratio</StyledTableCell>
              <StyledTableCell align="right">Breakout Price</StyledTableCell>
              <StyledTableCell align="right">EOD Price</StyledTableCell>
              <StyledTableCell align="center">Status</StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((performer, index) => (
              <TableRow 
                key={performer.symbol}
                sx={{ 
                  '&:hover': { 
                    backgroundColor: 'grey.50',
                    transform: 'scale(1.01)',
                    transition: 'all 0.2s ease-in-out'
                  },
                  '&:last-child td, &:last-child th': { border: 0 }
                }}
              >
                <SymbolCell>
                  <Avatar 
                    sx={{ 
                      width: 32, 
                      height: 32, 
                      bgcolor: 'primary.main',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}
                  >
                    {index + 1}
                  </Avatar>
                  <Typography variant="body1" fontWeight={600}>
                    {performer.symbol}
                  </Typography>
                </SymbolCell>
                
                <TableCell align="right">
                  <Chip
                    label={formatProbabilityScore(performer.probabilityScore)}
                    color={getProbabilityColor(performer.probabilityScore)}
                    variant="filled"
                    size="small"
                    sx={{ fontWeight: 600, minWidth: 60 }}
                  />
                </TableCell>
                
                <TableCell align="right">
                  <Typography 
                    variant="body2" 
                    fontWeight={600}
                    color={getPriceChangeColor(performer.priceChange) === 'success' ? 'success.main' : 'error.main'}
                  >
                    {formatPercentage(performer.priceChange)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatVolumeRatio(performer.volumeRatio)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatCurrency(performer.breakoutPrice)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatCurrency(performer.eodPrice)}
                  </Typography>
                </TableCell>
                
                <TableCell align="center">
                  <Chip
                    label={performer.status === 'successful' ? '✅' : '❌'}
                    color={getStatusColor(performer.status)}
                    variant="outlined"
                    size="small"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </ListContainer>
  );
};

export default TopPerformersList;