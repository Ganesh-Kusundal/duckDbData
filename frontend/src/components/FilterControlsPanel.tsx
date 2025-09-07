import React, { useState } from 'react';
import { 
  Paper, 
  Typography, 
  Stack, 
  TextField, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  Button,
  Box,
  Chip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import FilterAltOutlinedIcon from '@mui/icons-material/FilterAltOutlined';
import SyncOutlinedIcon from '@mui/icons-material/SyncOutlined';
import { ScannerType, TimeRange } from '../types/en