import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// The Flask API the dev server proxies /api to. Defaults to the documented
// http://localhost:5000. Set API_PROXY_TARGET in the environment to point the
// dev server at an API running on a different port (see the per-clone port
// block in the setup instructions).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'API_');

  return {
    plugins: [react()],
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
    server: {
      proxy: {
        '/api': {
          target: env.API_PROXY_TARGET || 'http://localhost:5000',
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: false,
      setupFiles: './src/test/setup.ts',
      include: ['src/**/*.test.{ts,tsx}'],
    },
  };
});
