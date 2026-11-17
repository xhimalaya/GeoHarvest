/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Source Sans 3"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      spacing: {
        '88': '22rem',
        '96': '24rem',
        '104': '26rem',
        '112': '28rem',
      },
      colors: {
        brand: {
          50: '#F8EDF0',
          100: '#F0D8E0',
          500: '#7D2142',
          600: '#641832',
          700: '#54162C',
          900: '#421B2A',
        },
        slate: {
          750: '#2D3733',
          850: '#252D2A',
          925: '#1D2422',
          950: '#1D2422',
        }
      }
    },
  },
  plugins: [],
}
