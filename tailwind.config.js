/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html','./src/**/*.{ts,js,html}'],
  darkMode: 'class',
  theme: { extend: {
    fontFamily: { sans: ['DM Sans','system-ui','sans-serif'], display: ['Plus Jakarta Sans','sans-serif'] },
    colors: { navy: '#0f2538', teal: '#087e81', mint: '#e6f7f1', greenx: '#10a978' },
    boxShadow: { panel: '0 3px 21px rgba(14,37,58,.055)' },
    borderRadius: { panel: '1.2rem' }
  } },
  plugins: []
};
