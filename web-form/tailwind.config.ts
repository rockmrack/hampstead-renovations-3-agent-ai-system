import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Hampstead Renovations brand colors
        hampstead: {
          50: '#f7f7f5',
          100: '#edede9',
          200: '#d5d5cc',
          300: '#b5b5a6',
          400: '#92917f',
          500: '#787764',
          600: '#5f5e50',
          700: '#4d4c41',
          800: '#404038',
          900: '#383831',
          950: '#1c1c18',
        },
        gold: {
          50: '#fdfce9',
          100: '#fbf9c6',
          200: '#f8f190',
          300: '#f3e350',
          400: '#edd321',
          500: '#d4b814',
          600: '#b8920f',
          700: '#936a10',
          800: '#7a5415',
          900: '#684518',
          950: '#3c240a',
        },
        navy: {
          50: '#f4f7fb',
          100: '#e8eef6',
          200: '#cbdaec',
          300: '#9dbbdc',
          400: '#6896c8',
          500: '#4579b2',
          600: '#346096',
          700: '#2b4d7a',
          800: '#274366',
          900: '#253956',
          950: '#0f1726',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Playfair Display', 'Georgia', 'serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-subtle': 'pulseSubtle 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.85' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config
