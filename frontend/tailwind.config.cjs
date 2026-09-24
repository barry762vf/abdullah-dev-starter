/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        arabic: ['Cairo', 'Tahoma', 'sans-serif'],
      },
      colors: {
        ink: '#17213a',
        muted: '#637087',
        accent: '#3265e9',
        surface: '#f7f8fb',
      },
      boxShadow: {
        panel: '0 16px 48px rgba(30, 46, 80, 0.08)',
      },
    },
  },
  plugins: [],
}
