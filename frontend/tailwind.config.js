/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      spacing: {
        '88': '22rem',
        '96': '24rem',
        '104': '26rem',
        '112': '28rem',
      },
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          900: '#0c4a6e',
        },
        slate: {
          750: '#293548',
          850: '#152033',
          925: '#0c1322',
          950: '#080d1a',
        }
      }
    },
  },
  plugins: [],
}
