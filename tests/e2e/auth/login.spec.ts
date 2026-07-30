import { expect, test } from '../fixtures/auth'

const TOKEN_STORAGE_KEY = `${process.env.VITE_APP_ID || 'pulse-db'}:token`

test.describe('E2E - Login', () => {
  test('should login with correct credentials via form', async ({ page, testUser }) => {
    // Navigate to login page
    await page.goto('/auth/login')

    // Verify we're on login page
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()

    // Fill login form
    await page.fill('input[type="email"]', testUser.email)
    await page.fill('input[type="password"]', testUser.password)

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for redirect to dashboard
    await page.waitForURL('**/dashboard', { timeout: 15000 })

    // Verify we're logged in
    expect(page.url()).toContain('/dashboard')

    // Verify token is stored in localStorage
    const token = await page.evaluate((tokenStorageKey) => localStorage.getItem(tokenStorageKey), TOKEN_STORAGE_KEY)
    expect(token).toBeTruthy()
    expect(token?.length).toBeGreaterThan(0)
  })

  test('should show error with incorrect password', async ({ page, testUser }) => {
    await page.goto('/auth/login')

    // Fill login form with wrong password
    await page.fill('input[type="email"]', testUser.email)
    await page.fill('input[type="password"]', 'wrong-password-123!')

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for error message to appear
    await page.waitForSelector('[role="alert"], .text-destructive, text=/invalid|incorrect|error|nieprawidłow/i', {
      timeout: 10000,
    })

    // Should still be on login page
    expect(page.url()).toContain('/auth/login')

    // Token should not be stored
    const token = await page.evaluate((tokenStorageKey) => localStorage.getItem(tokenStorageKey), TOKEN_STORAGE_KEY)
    expect(token).toBeNull()
  })

  test('should redirect authenticated user from login to dashboard', async ({ authenticatedPage }) => {
    // Already authenticated via fixture
    // Try to go to login page
    await authenticatedPage.goto('/auth/login')

    // Should redirect to dashboard (or stay there)
    await authenticatedPage.waitForURL('**/dashboard', { timeout: 10000 })
    expect(authenticatedPage.url()).toContain('/dashboard')
  })
})
