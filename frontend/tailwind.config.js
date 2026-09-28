export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0b0f1a', surface: '#131a2b', raised: '#1a2338', line: '#263150',
        text: '#e8ecf7', muted: '#98a3c0',
        primary: '#8b91ff', accent: '#3fd5e8',
        ok: '#4ade80', warn: '#fbbf24', bad: '#f87171',
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        sans: ['Figtree', 'system-ui', 'sans-serif'],
      },
    },
  },
}
