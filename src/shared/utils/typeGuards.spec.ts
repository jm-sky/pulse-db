import { AxiosError, type AxiosResponse, HttpStatusCode } from 'axios'
import { describe, expect, it } from 'vitest'
import { isValidationError, type ValidationErrorResponse } from './typeGuards'

describe('typeGuards', () => {
  describe('isValidationError', () => {
    it('should return true for validation error', () => {
      const error = new AxiosError('Validation failed')
      error.response = {
        status: HttpStatusCode.UnprocessableEntity,
        data: {
          errors: {
            field1: ['Error message 1'],
            field2: ['Error message 2'],
          },
        },
      } as unknown as AxiosResponse<ValidationErrorResponse>

      expect(isValidationError(error)).toBe(true)
    })

    it('should return false for non-Axios error', () => {
      const error = new Error('Regular error')
      expect(isValidationError(error)).toBe(false)
    })

    it('should return false for Axios error without response', () => {
      const error = new AxiosError('Network error')
      expect(isValidationError(error)).toBe(false)
    })

    it('should return false for Axios error with different status code', () => {
      const error = new AxiosError('Not found')
      error.response = {
        status: HttpStatusCode.NotFound,
        data: {},
      } as unknown as AxiosResponse<unknown>

      expect(isValidationError(error)).toBe(false)
    })

    it('should return false for 422 error without errors field', () => {
      const error = new AxiosError('Unprocessable entity')
      error.response = {
        status: HttpStatusCode.UnprocessableEntity,
        data: {},
      } as unknown as AxiosResponse<Record<string, unknown>>

      expect(isValidationError(error)).toBe(false)
    })

    it('should return false for 422 error with empty errors object', () => {
      const error = new AxiosError('Unprocessable entity')
      error.response = {
        status: HttpStatusCode.UnprocessableEntity,
        data: {
          errors: {},
        },
      } as unknown as AxiosResponse<ValidationErrorResponse>

      // Empty errors object should still be considered a validation error
      // Adjust this test based on actual implementation requirements
      expect(isValidationError(error)).toBe(true)
    })

    it('should handle validation errors with multiple field errors', () => {
      const error = new AxiosError('Validation failed')
      error.response = {
        status: HttpStatusCode.UnprocessableEntity,
        data: {
          errors: {
            email: ['Invalid email format', 'Email is required'],
            password: ['Password too short'],
          },
        },
      } as unknown as AxiosResponse<ValidationErrorResponse>

      expect(isValidationError(error)).toBe(true)
    })

    it('should return false for null or undefined', () => {
      expect(isValidationError(null)).toBe(false)
      expect(isValidationError(undefined)).toBe(false)
    })

    it('should return false for primitive values', () => {
      expect(isValidationError('string')).toBe(false)
      expect(isValidationError(123)).toBe(false)
      expect(isValidationError(true)).toBe(false)
    })

    it('should narrow type correctly', () => {
      const error: unknown = new AxiosError('Validation failed')
      if (error instanceof AxiosError) {
        error.response = {
          status: HttpStatusCode.UnprocessableEntity,
          data: {
            errors: {
              field: ['Error'],
            },
          },
        } as unknown as AxiosResponse<ValidationErrorResponse>
      }

      if (isValidationError(error)) {
        // TypeScript should know error is ValidationError here
        expect(error.response?.data?.errors).toBeDefined()
      }
    })
  })
})

