export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        farm: {
          bg:      '#0a0a0a',
          card:    '#111111',
          card2:   '#161616',
          border:  '#1e1e1e',
          border2: '#252525',
          muted:   '#444444',
          dim:     '#222222',
          text:    '#e8e8e8',
          sub:     '#666666',
          green:   '#00ff41',
          blue:    '#00aaff',
          red:     '#ff2040',
          amber:   '#ffaa00',
          purple:  '#cc55ff',
        },
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ["'JetBrains Mono'", 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
