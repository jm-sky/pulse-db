import axios from 'axios'
import { authInterceptor } from './auth.interceptor'
import { errorResponseInterceptor } from './error.interceptor'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 10000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: Add authentication token
apiClient.interceptors.request.use(authInterceptor)

// Response interceptor: Handle errors (401, etc.)
apiClient.interceptors.response.use(
  (response) => response,
  errorResponseInterceptor,
)
