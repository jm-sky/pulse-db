/**
 * Markdown Security Configuration
 * Limits and security settings for markdown content and links
 */

/**
 * Maximum length for a single link URL
 * RFC 7230: URL should not exceed 8000 characters, but 2048 is a safe practical limit
 */
export const MAX_LINK_LENGTH = 2048

/**
 * Maximum length for entire markdown content
 * PostgreSQL TEXT can store up to ~1GB, but 50000 characters is a reasonable limit
 * Prevents performance issues with rendering
 */
export const MAX_MARKDOWN_LENGTH = 50000

/**
 * Allowed protocols for links and images
 * Only HTTP and HTTPS are allowed for security
 */
export const ALLOWED_PROTOCOLS = ['http:', 'https:'] as const

/**
 * Blocked protocols that are considered dangerous
 * These protocols can execute code, access local files, or pose security risks
 */
export const BLOCKED_PROTOCOLS = [
  'javascript:',
  'data:',
  'vbscript:',
  'file:',
  'about:',
  'jar:',
  'chrome:',
  'chrome-extension:',
] as const

/**
 * Check if a protocol is allowed
 */
export function isProtocolAllowed(protocol: string): boolean {
  return ALLOWED_PROTOCOLS.includes(protocol.toLowerCase() as typeof ALLOWED_PROTOCOLS[number])
}

/**
 * Check if a protocol is blocked
 */
export function isProtocolBlocked(protocol: string): boolean {
  return BLOCKED_PROTOCOLS.some((blocked) =>
    protocol.toLowerCase().startsWith(blocked.toLowerCase())
  )
}

