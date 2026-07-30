/**
 * Validates avatar URL against allowed providers.
 * Only allows URLs from trusted avatar providers like Gravatar.
 */

const ALLOWED_AVATAR_PROVIDERS = [
  'gravatar.com',
  'www.gravatar.com',
  'secure.gravatar.com',
  'i0.wp.com', // WordPress CDN (often used for Gravatar)
  'i1.wp.com',
  'i2.wp.com',
]

export function validateAvatarUrl(url: string | null | undefined): boolean {
  if (!url || !url.trim()) {
    return true // Empty is allowed (will clear avatar)
  }

  try {
    const parsed = new URL(url)

    // Must be HTTPS
    if (parsed.protocol !== 'https:') {
      return false
    }

    // Check if hostname matches allowed providers
    const hostname = parsed.hostname.toLowerCase()
    const isAllowed = ALLOWED_AVATAR_PROVIDERS.some(
      provider => hostname === provider || hostname.endsWith(`.${provider}`)
    )

    if (!isAllowed) {
      return false
    }

    // Basic URL format validation
    if (!parsed.pathname) {
      return false
    }

    return true
  } catch {
    return false
  }
}
