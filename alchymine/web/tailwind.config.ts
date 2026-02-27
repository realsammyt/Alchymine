import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#DAA520',
          dark: '#B8860B',
          light: '#DAA520',
        },
        secondary: {
          DEFAULT: '#7B2D8E',
          dark: '#4A0E4E',
          light: '#7B2D8E',
        },
        accent: {
          DEFAULT: '#20B2AA',
          dark: '#008080',
          light: '#20B2AA',
        },
        bg: '#0A0A0F',
        surface: '#1A1A2E',
        text: '#F5F0E8',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      animation: {
        'shimmer': 'shimmer 2s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-gold': 'pulseGold 2s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGold: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(218, 165, 32, 0.4)' },
          '50%': { boxShadow: '0 0 20px 10px rgba(218, 165, 32, 0.1)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
