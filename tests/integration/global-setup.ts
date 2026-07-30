/**
 * Global setup for integration tests
 *
 * Creates test user via CLI if needed
 */

import { request } from '@playwright/test'
import { exec } from 'child_process'
import { config } from 'dotenv'
import { dirname, resolve } from 'path'
import { fileURLToPath } from 'url'
import { promisify } from 'util'

const execAsync = promisify(exec)

// Load .env
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
config({ path: resolve(__dirname, '../../.env') })

// Test user credentials
const TEST_USER = {
  email: process.env.E2E_TEST_USER_EMAIL || 'e2e-test@example.com',
  password: process.env.E2E_TEST_USER_PASSWORD || 'E2eTestPassword123!',
  name: 'E2E Test User',
}

const BACKEND_URL = 'http://localhost:8000'
const DOCKER_CONTAINER = 'pulse-db-app'

async function runDockerCommand(command: string): Promise<{ stdout: string; stderr: string }> {
  const fullCommand = `docker exec ${DOCKER_CONTAINER} ${command}`
  try {
    return await execAsync(fullCommand)
  } catch (error: unknown) {
    const execError = error as { stdout?: string; stderr?: string; message?: string }
    return {
      stdout: execError.stdout || '',
      stderr: execError.stderr || execError.message || '',
    }
  }
}

async function tryLogin(context: Awaited<ReturnType<typeof request.newContext>>): Promise<boolean> {
  try {
    const response = await context.post(`${BACKEND_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    })
    return response.ok()
  } catch {
    return false
  }
}

async function globalSetup() {
  console.log('\n🔧 Integration Tests Global Setup\n')

  const context = await request.newContext()

  // Check backend
  try {
    const health = await context.get(`${BACKEND_URL}/health`)
    if (!health.ok()) throw new Error('Backend not healthy')
  } catch {
    await context.dispose()
    throw new Error('Backend not available. Start with: docker compose -f docker-compose.dev.yml up -d')
  }

  // Try login
  if (await tryLogin(context)) {
    console.log('✓ Test user ready\n')
    await context.dispose()
    return
  }

  // Create user via CLI
  console.log('Creating test user...')
  await runDockerCommand(
    `python -m cli users create --no-input --email "${TEST_USER.email}" --name "${TEST_USER.name}" --password "${TEST_USER.password}"`,
  )
  await runDockerCommand(`python -m cli users verify-email "${TEST_USER.email}" --confirm --yes`)

  // Verify login works
  if (await tryLogin(context)) {
    console.log('✓ Test user created and ready\n')
    await context.dispose()
    return
  }

  await context.dispose()
  throw new Error('Failed to setup test user')
}

export default globalSetup
