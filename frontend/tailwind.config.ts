import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/lib/**/*.{js,ts,jsx,tsx,mdx}'
  ],
  theme: {
    extend: {
      colors: {
        ink: 'var(--color-ink)',
        paper: 'var(--color-paper)',
        sand: 'var(--color-sand)',
        moss: 'var(--color-moss)',
        coral: 'var(--color-coral)',
        line: 'var(--color-line)'
      },
      boxShadow: {
        glow: '0 20px 60px rgba(8, 15, 33, 0.16)'
      },
      backgroundImage: {
        'hero-radial': 'radial-gradient(circle at top left, rgba(218, 176, 115, 0.35), transparent 34%), radial-gradient(circle at bottom right, rgba(49, 121, 107, 0.18), transparent 40%)'
      }
    }
  },
  plugins: []
};

export default config;
