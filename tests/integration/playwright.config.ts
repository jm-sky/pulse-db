import { defineConfig } from '@playwright/test'
import { config } from 'dotenv'
import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'

// Get current directory for ES modules
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load .env file from project root
config({ path: resolve(__dirname, '../../.env') })

const BACKEND_URL = 'http://localhost:8000'

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  use: {
    baseURL: BACKEND_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'api',
      use: {},
    },
  ],
  // Global setup - creates test user if needed
  globalSetup: resolve(__dirname, 'global-setup.ts'),
})
