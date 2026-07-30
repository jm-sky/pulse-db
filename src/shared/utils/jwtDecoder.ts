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

/**
 * Whether an access token still requires 2FA verification, i.e. it was
 * issued with tfaPending=true and hasn't been verified yet.
 * Returns false (does not block navigation) if the token can't be decoded.
 */
export function requiresTwoFactorVerification(token: string): boolean {
  try {
    const payload = decodeJWT(token)
    return payload.tfaPending === true && payload.tfaVerified !== true
  } catch {
    return false
  }
}

