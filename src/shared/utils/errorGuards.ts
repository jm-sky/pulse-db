/**
 * Error Type Guards
 *
 * Utility functions to check error types and status codes.
 * Centralized to avoid duplication across modules.
 */

import { HttpStatusCode } from 'axios'

/**
 * Check if an error is an authentication error (401 or 403)
 *
 * @param error - Unknown error object
 * @returns true if error has 401 or 403 status code
 */
export function isAuthError(error: unknown): boolean {
  const errorObj = error as { response?: { status?: number } }
  if (!errorObj.response) return false
  const status = errorObj.response.status
  return status === HttpStatusCode.Unauthorized || status === HttpStatusCode.Forbidden
}

/**
 * Check if an error is a client error (4xx)
 *
 * @param error - Unknown error object
 * @returns true if error has 4xx status code
 */
export function isClientError(error: unknown): boolean {
  const errorObj = error as { response?: { status?: number } }
  if (!errorObj.response) return false
  const status = errorObj.response.status
  return !!status && status >= 400 && status < 500
}

/**
 * Check if an error is a server error (5xx)
 *
 * @param error - Unknown error object
 * @returns true if error has 5xx status code
 */
export function isServerError(error: unknown): boolean {
  const errorObj = error as { response?: { status?: number } }
  if (!errorObj.response) return false
  const status = errorObj.response.status
  return !!status && status >= 500 && status < 600
}

/**
 * Get error status code if available
 *
 * @param error - Unknown error object
 * @returns status code or undefined
 */
export function getErrorStatus(error: unknown): number | undefined {
  const errorObj = error as { response?: { status?: number } }
  return errorObj.response?.status
}

