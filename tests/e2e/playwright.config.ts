import { defineConfig, devices } from '@playwright/test'
import { config } from 'dotenv'
import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'

// Get current directory for ES modules
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load .env file from project root
config({ path: resolve(__dirname, '../../.env') })

// Get port from environment variable (VITE_PORT from .env) or use default
const FRONTEND_PORT = process.env.VITE_PORT || '5176'
const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 30000,
  expect: {
    timeout: 10000,
  },
  use: {
    baseURL: FRONTEND_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Global setup - creates test user if needed
  globalSetup: resolve(__dirname, 'global-setup.ts'),
  // Note: Frontend and backend must be started manually before running tests
  // Frontend: pnpm dev
  // Backend: docker compose -f docker-compose.dev.yml up -d
})
