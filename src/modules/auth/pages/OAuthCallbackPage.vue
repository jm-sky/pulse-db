<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useRecaptcha } from '@/shared/composables/useRecaptcha'
import type { AuthResponse, LoginResponse } from '../types/user.type'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { getToken } = useRecaptcha()

const isProcessing = ref(false)
const error = ref<string | null>(null)
const provider = ref('')

onMounted(async () => {
  if (isProcessing.value) return

  isProcessing.value = true

  try {
    // Get OAuth parameters from URL
    const code = route.query.code as string
    const state = route.query.state as string
    const errorParam = route.query.error as string
    const providerParam = (route.params.provider as string) || ''

    provider.value = providerParam

    // Handle OAuth error (user denied)
    if (errorParam) {
      error.value = t('auth.oauth.callback.cancelled_or_denied')
      setTimeout(() => {
        router.push(AuthRoutePaths.login)
      }, 2000)
      return
    }

    // Validate required parameters
    if (!providerParam || !code || !state) {
      error.value = t('auth.oauth.callback.invalid_parameters')
      setTimeout(() => {
        router.push(AuthRoutePaths.login)
      }, 2000)
      return
    }

    // CSRF `state` is verified server-side (oauth_state_store) on the callback API.

    // Get reCAPTCHA token if enabled
    const recaptchaToken = await getToken('oauth_callback')

    // Call OAuth callback endpoint
    const response: LoginResponse = await authService.oauthCallback(providerParam, {
      code,
      state,
      recaptchaToken,
    })

    // Handle response
    if ('requiresTwoFactor' in response && response.requiresTwoFactor) {
      authStore.setTwoFactorToken(
        response.twoFactorToken,
        response.methods,
        response.preferredMethod
      )
      await router.push(AuthRoutePaths.twoFactorVerify)
      return
    }

    const authResponse = response as AuthResponse

    // Success - set auth data and redirect (refresh token is an HttpOnly cookie)
    authStore.setToken(authResponse.accessToken)
    // Map avatarUrl from backend to avatar in frontend
    authStore.setUser({
      ...authResponse.user,
      avatarUrl: authResponse.user.avatarUrl,
    })
    toast.success(t('auth.oauth.callback.success', { provider: providerParam }))
    await router.push(AuthRoutePaths.dashboard)
  } catch (err: unknown) {
    console.error('OAuth callback error:', err)

    // Better error handling - extract message from API response
    let errorMessage = t('auth.oauth.callback.failed')

    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        errorMessage = axiosError.response.data.detail
      }
    } else if (err instanceof Error) {
      errorMessage = err.message
    }

    error.value = errorMessage
    console.error('OAuth callback detailed error:', errorMessage)
    toast.error(errorMessage)

    setTimeout(() => {
      router.push(AuthRoutePaths.login)
    }, 3000)
  } finally {
    isProcessing.value = false
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4 py-12">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle v-if="error" class="text-destructive">
          {{ t('auth.oauth.callback.authentication_failed') }}
        </CardTitle>
        <CardTitle v-else class="flex items-center">
          <div class="mr-2 size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          {{ t('auth.oauth.callback.signing_in') }}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription v-if="error">
          {{ error }}
        </CardDescription>
        <CardDescription v-else>
          {{ t('auth.oauth.callback.processing', { provider }) }}
        </CardDescription>
      </CardContent>
    </Card>
  </div>
</template>
