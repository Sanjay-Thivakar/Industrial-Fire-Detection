import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load server-side environment variables on the Node.js process (NOT exposed to browser bundle)
  const env = loadEnv(mode, process.cwd(), '');
  const apiKey =
    env.ML_API_KEY ||
    process.env.ML_API_KEY ||
    env.API_KEY ||
    process.env.API_KEY ||
    'test-api-key-phase5c';

  const apiHost =
    env.API_HOST ||
    process.env.API_HOST ||
    '127.0.0.1';
  const apiPort =
    env.API_PORT ||
    process.env.API_PORT ||
    '8000';

  const apiProxy = {
    '/api': {
      target: `http://${apiHost}:${apiPort}`,
      changeOrigin: true,
      headers: {
        'X-API-Key': apiKey,
      },
    },
  };

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: apiProxy,
    },
    preview: {
      host: '127.0.0.1',
      port: 4173,
      proxy: apiProxy,
    },
  };
});

