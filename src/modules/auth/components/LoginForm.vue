<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Alert from '@/components/ui/alert/Alert.vue'
import AlertDescription from '@/components/ui/alert/AlertDescription.vue'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import PasswordInput from '@/components/ui/input/PasswordInput.vue'
import OAuthFacebookButton from '@/modules/auth/components/OAuthFacebookButton.vue'
import OAuthGitHubButton from '@/modules/auth/components/OAuthGitHubButton.vue'
import OAuthGoogleButton from '@/modules/auth/components/OAuthGoogleButton.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRouteNames, AuthRoutePaths } from '@/modules/auth/config/routes'
import { loginSchema } from '@/modules/auth/validation/login.schema'
import { useHandleError } from '@/shared/composables/useHandleError'
import { useRecaptcha } from '@/shared/composables/useRecaptcha'
import { config } from '@/shared/config/config'
import { isUnauthorizedFormError } from '@/shared/utils/typeGuards'
import type { IAuthService } from '@/modules/auth/types/auth.type'
import type { LoginCredentials } from '@/modules/auth/types/user.type'

const { authService, defaultEmail } = defineProps<{
  authService?: IAuthService
  defaultEmail?: string
}>()

const emit = defineEmits<{
  success: []
}>()

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const { login, isLoggingIn } = useAuth(authService)
const { getToken } = useRecaptcha()
const { handleUnauthorizedFormError } = useHandleError()

const formError = ref<string | null>(null)

const { handleSubmit, setErrors } = useForm({
  validationSchema: toTypedSchema(loginSchema),
  initialValues: {
    email: defaultEmail ?? import.meta.env.VITE_DEFAULT_USER_EMAIL ?? '',
    password: import.meta.env.VITE_DEFAULT_USER_PASSWORD ?? '',
  },
})

const onSubmit = handleSubmit(async (values: LoginCredentials) => {
  formError.value = null
  try {
    // Get reCAPTCHA token before login
    const recaptchaToken = await getToken('login')

    const response = await login({
      ...values,
      recaptchaToken,
    })

    // Check if 2FA is required
    if ('requiresTwoFactor' in response && response.requiresTwoFactor) {
      // Redirect to 2FA verification page
      await router.push({
        name: AuthRouteNames.twoFactorVerify,
        query: { redirectTo: typeof route.query.redirectTo === 'string' ? route.query.redirectTo : AuthRoutePaths.dashboard },
      })
      return
    }

    // Check if email verification is required (only for normal auth response)
    if ('requiresEmailVerification' in response && response.requiresEmailVerification) {
      toast.info(t('auth.verify_email_required'))
      await router.push({ name: AuthRouteNames.verifyEmail, query: { email: values.email } })
      return
    }

    // Normal login success - emit success event and redirect to dashboard
    emit('success')
    const redirectTo = typeof route.query.redirectTo === 'string' ? route.query.redirectTo : undefined
    await router.push(redirectTo ?? AuthRoutePaths.dashboard)
  } catch (err: unknown) {
    if (isUnauthorizedFormError(err)) {
      formError.value = t('auth.invalid_credentials')
      return
    }
    handleUnauthorizedFormError(err, setErrors)
  }
})
</script>

<template>
  <form class="space-y-4" @submit="onSubmit">
    <FormField v-slot="{ componentField }" name="email">
      <FormItem>
        <FormLabel required>
          {{ t('auth.email') }}
        </FormLabel>
        <FormControl>
          <Input type="email" :placeholder="t('auth.form.email_placeholder')" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <FormField v-slot="{ componentField }" name="password">
      <FormItem>
        <FormLabel required>
          {{ t('auth.password') }}
        </FormLabel>
        <FormControl>
          <PasswordInput :placeholder="t('auth.form.password_placeholder')" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <Alert v-if="formError" variant="destructive" role="alert">
      <AlertDescription>{{ formError }}</AlertDescription>
    </Alert>

    <Button type="submit" class="w-full" :loading="isLoggingIn">
      {{ t('auth.form.submit_login') }}
    </Button>

    <template v-if="config.oauth.google.enabled || config.oauth.facebook.enabled || config.oauth.github.enabled">
      <div class="relative my-6">
        <div class="absolute inset-0 flex items-center">
          <span class="w-full border-t" />
        </div>
        <div class="relative flex justify-center text-xs uppercase">
          <span class="bg-background px-2 text-muted-foreground">
            {{ t('auth.oauth.or_continue_with') }}
          </span>
        </div>
      </div>

      <OAuthGoogleButton v-if="config.oauth.google.enabled" />
      <OAuthFacebookButton v-if="config.oauth.facebook.enabled" />
      <OAuthGitHubButton v-if="config.oauth.github.enabled" />
    </template>
  </form>
</template>
