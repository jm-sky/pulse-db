import { test as base, expect } from '@playwright/test'
import { config } from 'dotenv'
import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'
import type { Page } from '@playwright/test'

// Load .env
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
config({ path: resolve(__dirname, '../../../.env') })

// Test user credentials
const TEST_USER = {
  email: process.env.E2E_TEST_USER_EMAIL || 'e2e-test@example.com',
  password: process.env.E2E_TEST_USER_PASSWORD || 'E2eTestPassword123!',
}
const TOKEN_STORAGE_KEY = `${process.env.VITE_APP_ID || 'pulse-db'}:token`

type AuthFixtures = {
  authenticatedPage: Page
  testUser: { email: string; password: string }
}

export const test = base.extend<AuthFixtures>({
  testUser: async ({}, use) => {
    await use(TEST_USER)
  },

  authenticatedPage: async ({ page, testUser }, use) => {
    // Navigate to login page
    await page.goto('/auth/login')

    // Fill login form
    await page.fill('input[type="email"]', testUser.email)
    await page.fill('input[type="password"]', testUser.password)

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for redirect to dashboard (or any authenticated page)
    await page.waitForURL('**/dashboard', { timeout: 15000 })

    // Verify token is stored
    const token = await page.evaluate((tokenStorageKey) => localStorage.getItem(tokenStorageKey), TOKEN_STORAGE_KEY)
    if (!token) {
      throw new Error('Login failed - no token in localStorage')
    }

    await use(page)
  },
})

export { expect }
