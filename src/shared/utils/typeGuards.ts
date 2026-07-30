// shared/utils/typeGuards.ts
import { type AxiosError, type AxiosResponse, HttpStatusCode, isAxiosError } from 'axios'

export interface ValidationErrorResponse {
  errors: Record<string, string[]>
}

export type ValidationError = AxiosError<ValidationErrorResponse> & {
  response: AxiosResponse<ValidationErrorResponse>
}

export function isValidationError(err: unknown): err is ValidationError {
  return isAxiosError(err) && err.response?.status === HttpStatusCode.UnprocessableEntity && !!err.response.data?.errors
}

// Unauthorized error response can have either `errors` (field-specific) or `detail` (general message)
export interface UnauthorizedErrorResponse {
  errors?: Record<string, string[]>
  detail?: string
}

export type UnauthorizedError = AxiosError<UnauthorizedErrorResponse> & {
  response: AxiosResponse<UnauthorizedErrorResponse>
}

// Matches any 401 Unauthorized response - the handler provides fallback for missing `errors` key
export function isUnauthorizedFormError(err: unknown): err is UnauthorizedError {
  return isAxiosError(err) && err.response?.status === HttpStatusCode.Unauthorized
}
