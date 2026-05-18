import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:3041',
      '/status': 'http://localhost:3041',
      '/history': 'http://localhost:3041',
      '/retail-analyze': 'http://localhost:3041',
      '/retail-status': 'http://localhost:3041',
      '/stock': 'http://localhost:3041',
      '/send-report': 'http://localhost:3041',
      '/screen': 'http://localhost:3041',
    },
  },
});
