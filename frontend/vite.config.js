import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  envDir: '..',
  envPrefix: ['VITE_', 'NEON_AUTH_BASE_URL'],
  server: { proxy: { '/dashboard': 'http://127.0.0.1:8000', '/inventory': 'http://127.0.0.1:8000', '/products': 'http://127.0.0.1:8000', '/users': 'http://127.0.0.1:8000', '/voice': { target: 'http://127.0.0.1:8000', ws: true } } },
  build: { outDir: 'dist', emptyOutDir: true },
});
