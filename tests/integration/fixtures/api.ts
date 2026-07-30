import { test as base, request } from '@playwright/test'
import { config } from 'dotenv'
import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'
import type { APIRequestContext } from '@playwright/test'

// Load .env
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
config({ path: resolve(__dirname, '../../../.env') })

// Test user credentials
const TEST_USER = {
  email: process.env.E2E_TEST_USER_EMAIL || 'e2e-test@example.com',
  password: process.env.E2E_TEST_USER_PASSWORD || 'E2eTestPassword123!',
}

const BACKEND_URL = 'http://localhost:8000'

type ApiFixtures = {
  apiContext: APIRequestContext
  testUser: { email: string; password: string }
}

export const test = base.extend<ApiFixtures>({
  testUser: async ({}, use) => {
    await use(TEST_USER)
  },

  apiContext: async ({}, use) => {
    // Login to get token
    const loginContext = await request.newContext()
    const response = await loginContext.post(`${BACKEND_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    })

    if (!response.ok()) {
      await loginContext.dispose()
      throw new Error(`Login failed: ${response.status()}`)
    }

    const { accessToken } = await response.json()
    await loginContext.dispose()

    // Create API context with auth
    const apiContext = await request.newContext({
      baseURL: BACKEND_URL,
      extraHTTPHeaders: {
        Authorization: `Bearer ${accessToken}`,
      },
    })

    await use(apiContext)
    await apiContext.dispose()
  },
})

export { expect } from '@playwright/test'
