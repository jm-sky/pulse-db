// features/tenantFeat/lib/jwtDecoder.ts
import { jwtDecode } from 'jwt-decode'
import type { JWTPayload } from '../types/jwt.type'

/**
 * Decode JWT token and return payload
 * Supports both real JWT tokens and mock tokens (for demo)
 */
export function decodeJWT(token: string): JWTPayload {
  // Handle real JWT tokens
  try {
    return jwtDecode<JWTPayload>(token)
  } catch (error) {
    console.error('Error decoding JWT token:', error)
    throw new Error('Invalid JWT token')
  }
}

