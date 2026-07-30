/**
 * Double-submit CSRF helpers for cookie-authenticated API calls.
 *
 * Backend sets a non-HttpOnly `csrf_token` cookie (Path=/). The SPA must
 * echo it in the `X-CSRF-Token` header on POST/PUT/PATCH/DELETE.
 */

import axios from 'axios'

export const CSRF_COOKIE_NAME = 'csrf_token'
export const CSRF_HEADER_NAME = 'X-CSRF-Token'

const UNSAFE_METHODS = new Set(['delete', 'patch', 'post', 'put'])

let memoryCsrfToken: string | null = null

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? '/api'
}

export function readCsrfTokenFromCookie(): string | null {
  if (typeof document === 'undefined') {
    return null
  }
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)
  if (!match?.[1]) {
    return null
  }
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

export function getCsrfToken(): string | null {
  const fromCookie = readCsrfTokenFromCookie()
  if (fromCookie) {
    memoryCsrfToken = fromCookie
    return fromCookie
  }
  return memoryCsrfToken
}

export function isUnsafeHttpMethod(method: string | undefined): boolean {
  return UNSAFE_METHODS.has((method ?? 'get').toLowerCase())
}

/**
 * Ensure a CSRF cookie/token exists before the first mutating API call
 * (e.g. silent refresh on boot). Uses a bare axios call to avoid interceptor cycles.
 */
export async function ensureCsrfToken(): Promise<string> {
  const existing = getCsrfToken()
  if (existing) {
    return existing
  }

  const { data } = await axios.get<{ csrf_token: string }>(
    `${apiBaseUrl()}/auth/csrf-token`,
    { withCredentials: true },
  )
  memoryCsrfToken = data.csrf_token
  return memoryCsrfToken
}
