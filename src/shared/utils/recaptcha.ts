import { config } from '@/shared/config/config'

let recaptchaLoaded = false
let recaptchaLoadPromise: Promise<void> | null = null

/**
 * Load reCAPTCHA v3 script
 */
export function loadRecaptchaScript(): Promise<void> {
  if (recaptchaLoaded) {
    return Promise.resolve()
  }

  if (recaptchaLoadPromise) {
    return recaptchaLoadPromise
  }

  if (!config.recaptcha.enabled) {
    return Promise.resolve()
  }

  recaptchaLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://www.google.com/recaptcha/api.js?render=${config.recaptcha.siteKey}`
    script.async = true
    script.defer = true

    script.onload = () => {
      recaptchaLoaded = true
      resolve()
    }

    script.onerror = () => {
      reject(new Error('Failed to load reCAPTCHA script'))
    }

    document.head.appendChild(script)
  })

  return recaptchaLoadPromise
}

/**
 * Execute reCAPTCHA and get token
 *
 * Note: reCAPTCHA tokens expire after ~2 minutes and are single-use.
 * Generate tokens immediately before making API calls.
 */
export async function executeRecaptcha(action: string): Promise<string | null> {
  if (!config.recaptcha.enabled) {
    return null
  }

  try {
    await loadRecaptchaScript()

    if (!window.grecaptcha) {
      console.warn('[reCAPTCHA] Script not loaded - grecaptcha not available')
      return null
    }

    // Ensure grecaptcha is ready
    await new Promise<void>((resolve) => {
      if (window.grecaptcha.ready) {
        window.grecaptcha.ready(() => resolve())
      } else {
        // Fallback if ready callback is not available
        resolve()
      }
    })

    const token = await window.grecaptcha.execute(config.recaptcha.siteKey, { action })

    if (!token) {
      console.warn('[reCAPTCHA] Token generation returned empty token')
      return null
    }

    return token
  } catch (error) {
    console.error('[reCAPTCHA] Execution failed:', error)
    return null
  }
}

// Type declaration for window.grecaptcha
declare global {
  interface Window {
    grecaptcha: {
      execute: (siteKey: string, options: { action: string }) => Promise<string>
      ready: (callback: () => void) => void
      render?: (container: string | HTMLElement, parameters: Record<string, unknown>) => number
    }
  }
}
