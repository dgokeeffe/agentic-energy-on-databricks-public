import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: { baseURL: 'http://localhost:8000', channel: 'chrome' },
  webServer: {
    command: 'npm run build:client && npx vite preview --config client/vite.config.ts --host 127.0.0.1 --port 8000',
    url: 'http://localhost:8000',
    reuseExistingServer: false,
    timeout: 90_000,
    env: { ...process.env, VITE_DATA_MODE: 'mock' },
  },
});
