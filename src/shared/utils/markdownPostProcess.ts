/**
 * Markdown Post-Processing Utilities
 * Functions for sanitizing and securing rendered markdown HTML
 */

import { MAX_LINK_LENGTH } from '../config/markdownSecurity'
import {
  isDangerousProtocol,
  isExternalLink,
  validateLinkLength,
} from './linkSecurity'

/**
 * Post-process rendered markdown HTML to secure links
 * - Adds rel="noopener noreferrer" to external links
 * - Removes or disables dangerous protocol links
 * - Validates link length
 */
export function secureMarkdownHtml(html: string): string {
  if (!html) {
    return html
  }

  // Use DOMParser for better HTML parsing (browser only)
  if (typeof window === 'undefined') {
    // SSR fallback - basic regex-based sanitization
    return sanitizeHtmlWithRegex(html)
  }

  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const links = doc.querySelectorAll('a')

    links.forEach((link) => {
      const href = link.getAttribute('href')
      if (!href) {
        return
      }

      // Check if link is too long
      if (!validateLinkLength(href, MAX_LINK_LENGTH)) {
        // Remove href and add disabled class
        link.removeAttribute('href')
        link.classList.add('link-disabled')
        link.setAttribute('title', 'Link is too long and has been disabled')
        return
      }

      // Check for dangerous protocols
      if (isDangerousProtocol(href)) {
        // Remove href and add disabled class
        link.removeAttribute('href')
        link.classList.add('link-disabled')
        link.setAttribute('title', 'Dangerous protocol has been blocked')
        return
      }

      // Add rel="noopener noreferrer" to external links
      if (isExternalLink(href)) {
        const currentRel = link.getAttribute('rel') || ''
        const relParts = currentRel.split(/\s+/).filter(Boolean)
        if (!relParts.includes('noopener')) {
          relParts.push('noopener')
        }
        if (!relParts.includes('noreferrer')) {
          relParts.push('noreferrer')
        }
        link.setAttribute('rel', relParts.join(' '))
        link.setAttribute('target', '_blank')
      }
    })

    return doc.body.innerHTML
  } catch (error) {
    console.error('Error processing markdown HTML:', error)
    // Fallback to regex-based sanitization
    return sanitizeHtmlWithRegex(html)
  }
}

/**
 * Fallback regex-based HTML sanitization for SSR or when DOMParser fails
 */
function sanitizeHtmlWithRegex(html: string): string {
  // Match <a> tags with href attribute
  return html.replace(/<a\s+([^>]*?)href=["']([^"']+)["']([^>]*?)>/gi, (match, before, href, after) => {
    // Check if link is too long
    if (!validateLinkLength(href, MAX_LINK_LENGTH)) {
      return `<a ${before}${after} class="link-disabled" title="Link is too long and has been disabled">`
    }

    // Check for dangerous protocols
    if (isDangerousProtocol(href)) {
      return `<a ${before}${after} class="link-disabled" title="Dangerous protocol has been blocked">`
    }

    // Add rel="noopener noreferrer" to external links
    if (isExternalLink(href)) {
      const relMatch = before.match(/rel=["']([^"']+)["']/i) || after.match(/rel=["']([^"']+)["']/i)
      let rel = relMatch ? relMatch[1] : ''
      const relParts = rel.split(/\s+/).filter(Boolean)
      if (!relParts.includes('noopener')) {
        relParts.push('noopener')
      }
      if (!relParts.includes('noreferrer')) {
        relParts.push('noreferrer')
      }
      rel = relParts.join(' ')

      // Remove existing rel and target attributes
      const cleanedBefore = before.replace(/rel=["'][^"']*["']/gi, '').replace(/target=["'][^"']*["']/gi, '')
      const cleanedAfter = after.replace(/rel=["'][^"']*["']/gi, '').replace(/target=["'][^"']*["']/gi, '')

      return `<a ${cleanedBefore}href="${href}" rel="${rel}" target="_blank"${cleanedAfter}>`
    }

    return match
  })
}

