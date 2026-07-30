import { isAxiosError } from 'axios'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { isUnauthorizedFormError, isValidationError } from '../utils/typeGuards'

interface HandleErrorOptions {
  setErrors?: (errors: Record<string, string[]>) => void
  fallbackMessage?: string
}

export const useHandleError = () => {
  const { t } = useI18n()

  const handleError = (
    error: unknown,
    { setErrors, fallbackMessage }: HandleErrorOptions = {}
  ) => {
    if (isValidationError(error) && setErrors) {
      setErrors(error.response.data.errors)
    } else if (isAxiosError(error)) {
      toast.error(error.response?.data.message ?? error.response?.data.detail ?? (fallbackMessage ?? t('errors.generic')))
    } else {
      toast.error(fallbackMessage ?? t('errors.generic'))
    }
  }

  const handleUnauthorizedFormError = (error: unknown, setErrors?: (errors: Record<string, string[]>) => void) => {
    if (isUnauthorizedFormError(error) && setErrors) {
      setErrors(error.response.data.errors ?? {
        email: [t('auth.invalid_credentials')],
        password: [t('auth.invalid_credentials')],
      })
    } else if (isAxiosError(error)) {
      toast.error(error.response?.data.message ?? error.response?.data.detail ?? t('errors.unauthorized'))
    } else {
      console.error('Unexpected error:', error)
      toast.error(t('errors.unauthorized'))
    }
  }

  return {
    handleError,
    handleUnauthorizedFormError,
  }
}
