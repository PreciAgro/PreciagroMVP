/**
 * PreciAgro Design System
 * World-class design tokens for professional agricultural intelligence UI
 */

export const DesignTokens = {
  colors: {
    // Core Palette
    background: {
      primary: '#000000',
      secondary: '#0c0c0c',
      surface: '#161616',
      overlay: 'rgba(255, 255, 255, 0.05)',
    },
    
    text: {
      primary: '#FAFAFA',
      secondary: '#A0A0A0',
      tertiary: '#666666',
      disabled: '#444444',
    },
    
    // Semantic Colors (HSL for consistency)
    semantic: {
      success: {
        base: 'hsl(142, 71%, 45%)',
        light: 'hsl(142, 71%, 55%)',
        dark: 'hsl(142, 71%, 35%)',
      },
      warning: {
        base: 'hsl(38, 92%, 50%)',
        light: 'hsl(38, 92%, 60%)',
        dark: 'hsl(38, 92%, 40%)',
      },
      danger: {
        base: 'hsl(0, 84%, 60%)',
        light: 'hsl(0, 84%, 70%)',
        dark: 'hsl(0, 84%, 50%)',
      },
      info: {
        base: 'hsl(217, 91%, 60%)',
        light: 'hsl(217, 91%, 70%)',
        dark: 'hsl(217, 91%, 50%)',
      },
    },
    
    // UI Elements
    border: {
      default: 'rgba(255, 255, 255, 0.08)',
      hover: 'rgba(255, 255, 255, 0.12)',
      focus: 'rgba(255, 255, 255, 0.16)',
    },
  },
  
  // 8pt Grid Spacing System
  spacing: {
    0.5: '4px',
    1: '8px',
    1.5: '12px',
    2: '16px',
    3: '24px',
    4: '32px',
    6: '48px',
    8: '64px',
    12: '96px',
    16: '128px',
  },
  
  // Typography Scale
  typography: {
    fontFamily: {
      primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
    },
    
    fontSize: {
      xs: '12px',
      sm: '14px',
      base: '16px',
      lg: '20px',
      xl: '24px',
      '2xl': '32px',
      '3xl': '48px',
    },
    
    fontWeight: {
      light: 300,
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.6,
    },
    
    letterSpacing: {
      tight: '-0.02em',
      normal: '0',
      wide: '0.05em',
    },
  },
  
  // Tesla-Grade Motion
  motion: {
    duration: {
      micro: '150ms',
      small: '250ms',
      medium: '400ms',
      large: '600ms',
    },
    
    easing: {
      outExpo: 'cubic-bezier(0.16, 1, 0.3, 1)',
      inOutCirc: 'cubic-bezier(0.85, 0, 0.15, 1)',
      spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
  
  // Layout
  layout: {
    containerMaxWidth: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
    },
    
    zIndex: {
      base: 0,
      dropdown: 10,
      modal: 20,
      overlay: 30,
      critical: 50,
    },
  },
  
  // Effects
  effects: {
    glassmorphism: {
      background: 'rgba(22, 22, 22, 0.7)',
      backdropFilter: 'blur(20px) saturate(180%)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
    },
    
    shadow: {
      sm: '0 1px 2px 0 rgba(0, 0, 0, 0.5)',
      md: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
      lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
      xl: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
    },
  },
} as const;

export type DesignSystem = typeof DesignTokens;
