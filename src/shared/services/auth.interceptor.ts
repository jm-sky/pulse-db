import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import {
  CSRF_HEADER_NAME,
  ensureCsrfToken,
  getCsrfToken,
  isUnsafeHttpMethod,
} from './csrf'
import type { InternalAxiosRequestConfig } from 'axios'

export async function authInterceptor(
  config: InternalAxiosRequestConfig,
): Promise<InternalAxiosRequestConfig> {
  const token = useAuthStore().token

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (isUnsafeHttpMethod(config.method)) {
    let csrfToken = getCsrfToken()
    if (!csrfToken) {
      csrfToken = await ensureCsrfToken()
    }
    if (csrfToken) {
      config.headers[CSRF_HEADER_NAME] = csrfToken
    }
  }

  return config
}
