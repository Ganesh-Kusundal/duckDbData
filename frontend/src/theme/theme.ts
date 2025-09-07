// Enhanced theme for the breakout scanner dashboard
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
      light: '#9bb5ff',
      dark: '#3f51b5',
      contrastText: '#ffffff'
    },
    secondary: {
      main: '#764ba2',
      light: '#a777d9',
      dark: '#512da8',
      contrastText: '#ffffff'
    },
    success: {
      main: '#28a745',
      light: '#71dd8a',
      dark: '#1e7e34',
      contrastText: '#ffffff'
    },
    error: {
      main: '#dc3545',
      light: '#f1788d',
      dark: '#bd2130',
      contrastText: '#ffffff'
    },
    warning: {
      main: '#ffc107',
      light: '#fff350',
      dark: '#ff8f00',
      contrastText: '#000000'
    },
    info: {
      main: '#17a2b8',
      light: '#6ec6ff',
      dark: '#0277bd',
      contrastText: '#ffffff'
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff'
    },
    text: {
      primary: '#2c3e50',
      secondary: '#6c757d'
    },
    grey: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#9e9e9e',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121'
    }
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      lineHeight: 1.2
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.3
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.4
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.4
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.43
    }
  },
  shape: {
    borderRadius: 12
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0,0,0,0.1)',
    '0px 4px 8px rgba(0,0,0,0.1)',
    '0px 8px 16px rgba(0,0,0,0.1)',
    '0px 12px 24px rgba(0,0,0,0.1)',
    '0px 16px 32px rgba(0,0,0,0.1)',
    '0px 20px 40px rgba(0,0,0,0.1)',
    '0px 24px 48px rgba(0,0,0,0.1)',
    '0px 28px 56px rgba(0,0,0,0.1)',
    '0px 32px 64px rgba(0,0,0,0.1)',
    '0px 36px 72px rgba(0,0,0,0.1)',
    '0px 40px 80px rgba(0,0,0,0.1)',
    '0px 44px 88px rgba(0,0,0,0.1)',
    '0px 48px 96px rgba(0,0,0,0.1)',
    '0px 52px 104px rgba(0,0,0,0.1)',
    '0px 56px 112px rgba(0,0,0,0.1)',
    '0px 60px 120px rgba(0,0,0,0.1)',
    '0px 64px 128px rgba(0,0,0,0.1)',
    '0px 68px 136px rgba(0,0,0,0.1)',
    '0px 72px 144px rgba(0,0,0,0.1)',
    '0px 76px 152px rgba(0,0,0,0.1)',
    '0px 80px 160px rgba(0,0,0,0.1)',
    '0px 84px 168px rgba(0,0,0,0.1)',
    '0px 88px 176px rgba(0,0,0,0.1)',
    '0px 92px 184px rgba(0,0,0,0.1)'
  ]
});

export default theme;