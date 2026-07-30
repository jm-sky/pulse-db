/**
 * Link Security Utilities
 * Functions for validating and sanitizing links in markdown content
 */

import {
  BLOCKED_PROTOCOLS,
  isProtocolAllowed,
  isProtocolBlocked,
  MAX_LINK_LENGTH,
  MAX_MARKDOWN_LENGTH,
} from '../config/markdownSecurity'

/**
 * Check if a URL is external (not relative and not same origin)
 */
export function isExternalLink(url: string): boolean {
  try {
    // Relative URLs are not external
    if (url.startsWith('/') || url.startsWith('./') || url.startsWith('../')) {
      return false
    }

    // Try to parse as absolute URL
    const parsed = new URL(url, window.location.origin)
    return parsed.origin !== window.location.origin
  } catch {
    // If parsing fails, treat as relative (not external)
    return false
  }
}

/**
 * Check if a protocol is dangerous
 */
export function isDangerousProtocol(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin)
    return isProtocolBlocked(parsed.protocol)
  } catch {
    // If parsing fails, check if URL starts with blocked protocol
    return BLOCKED_PROTOCOLS.some((protocol) =>
      url.toLowerCase().startsWith(protocol.toLowerCase())
    )
  }
}

/**
 * Sanitize a link by removing dangerous protocols
 * Returns null if protocol is blocked, otherwise returns sanitized URL
 */
export function sanitizeLink(url: string): string | null {
  if (isDangerousProtocol(url)) {
    return null
  }

  try {
    const parsed = new URL(url, window.location.origin)
    if (!isProtocolAllowed(parsed.protocol)) {
      return null
    }
    return parsed.toString()
  } catch {
    // If parsing fails, return null for safety
    return null
  }
}

/**
 * Validate link length
 * Returns true if link is within allowed length
 */
export function validateLinkLength(url: string, maxLength: number = MAX_LINK_LENGTH): boolean {
  return url.length <= maxLength
}

/**
 * Sanitize markdown content by removing dangerous links and validating length
 * Returns sanitized content or null if content is too long
 */
export function sanitizeMarkdownContent(
  content: string,
  maxLength: number = MAX_MARKDOWN_LENGTH
): string | null {
  if (content.length > maxLength) {
    return null
  }

  // Basic sanitization - remove dangerous protocols from URLs
  // This is a simple regex-based approach for basic protection
  // More complex parsing would be done in backend
  const dangerousProtocolPattern = new RegExp(
    `(${BLOCKED_PROTOCOLS.map((p) => p.replace(':', '\\:')).join('|')})[^\\s]*`,
    'gi'
  )

  return content.replace(dangerousProtocolPattern, '')
}

