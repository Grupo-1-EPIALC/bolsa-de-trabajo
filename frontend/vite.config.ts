import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// En Docker el front se sirve detrás del gateway (http://localhost:8080),
// así que la API es same-origin en /api/v1 y no hace falta proxy ni CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 8080,
    strictPort: true,
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
    hmr: { clientPort: Number(process.env.GATEWAY_PORT ?? 8080) },
  },
  test: { environment: 'node' },
});
