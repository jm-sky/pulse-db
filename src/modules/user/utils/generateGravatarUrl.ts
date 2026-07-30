/**
 * Generates a Gravatar URL from an email address.
 * Gravatar URLs use MD5 hash of the email (lowercased and trimmed).
 */

import md5 from 'md5'

export const GRAVATAR_BASE_URL = 'https://www.gravatar.com/avatar'

/**
 * Generates a Gravatar URL from an email address.
 * @param email - The email address to generate a Gravatar URL for
 * @returns The Gravatar URL
 */
export function generateGravatarUrl(email: string, size: number = 128): string {
  if (!email || !email.trim()) {
    throw new Error('Email is required to generate Gravatar URL')
  }

  // Gravatar requires lowercase, trimmed email
  const normalizedEmail = email.toLowerCase().trim()
  
  // Generate MD5 hash using the md5 package
  const hash = md5(normalizedEmail)
  
  // Return Gravatar URL
  return `${GRAVATAR_BASE_URL}/${hash}?d=404&s=${size}`
}
