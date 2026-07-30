<script setup lang="ts">
import { RotateCwIcon } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Alert from '@/components/ui/alert/Alert.vue'
import AlertDescription from '@/components/ui/alert/AlertDescription.vue'
import { Button } from '@/components/ui/button'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import GuestLayoutCentered from '@/layouts/GuestLayoutCentered.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'

type VerificationStatus = 'idle' | 'success' | 'error'

const REDIRECT_TIMEOUT = 3000

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { verifyEmail, resendVerification, isResendingVerification, isVerifyingEmail } = useAuth()

const verificationStatus = ref<VerificationStatus>('idle')
const verificationError = ref<string | null>(null)
const message = ref<string | null>(null)
const emailInput = ref<string>('')
const redirectTimeout = ref<number | null>(null)

const token = computed(() => typeof route.query.token === 'string' ? route.query.token : null)
const isVerified = computed(() => verificationStatus.value === 'success')

const existingEmail = computed(() => {
  if (typeof route.query.email === 'string') {
    return route.query.email
  }
  return authStore.user?.email ?? null
})

onMounted(async () => {
  emailInput.value = existingEmail.value ?? ''
  if (token.value) {
    await handleVerify(token.value)
  } else if (!existingEmail.value) {
    message.value = t('auth.verify_email.instructions')
  }
})

async function handleVerify(currentToken: string) {
  verificationStatus.value = 'idle'
  verificationError.value = null

  try {
    await verifyEmail(currentToken)
    verificationStatus.value = 'success'
    message.value = t('auth.verify_email.success')
    toast.success(t('auth.verify_email.success'))
    redirectTimeout.value = setTimeout(() => {
      router.push(AuthRoutePaths.login)
    }, REDIRECT_TIMEOUT)
  } catch (error) {
    verificationStatus.value = 'error'
    verificationError.value = t('auth.verify_email.invalid_or_expired')
    console.error('[VerifyEmailPage] verify error', error)
    toast.error(t('auth.verify_email.invalid_or_expired'))
  }
}

async function handleResend() {
  if (!emailInput.value) {
    toast.error(t('auth.verify_email.email_required'))
    return
  }

  try {
    const response = await resendVerification(emailInput.value)
    toast.success(response.message)
  } catch (error) {
    console.error('[VerifyEmailPage] resend error', error)
    toast.error(t('errors.generic'))
  }
}

onBeforeUnmount(() => {
  if (redirectTimeout.value) {
    clearTimeout(redirectTimeout.value)
  }
})
</script>

<template>
  <GuestLayoutCentered>
    <div class="max-w-lg w-full space-y-8 text-center bg-card shadow-lg rounded-lg p-8">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('auth.verify_email.title') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('auth.verify_email.subtitle') }}
        </p>
      </div>

      <div v-if="isVerifyingEmail" class="animate-pulse space-y-3">
        <div class="h-4 bg-muted rounded" />
        <div class="h-4 bg-muted rounded w-3/4 mx-auto" />
      </div>

      <div v-else class="space-y-4">
        <Alert v-if="message" variant="success">
          <AlertDescription>
            {{ message }}
          </AlertDescription>
        </Alert>
        <Alert v-if="verificationError" variant="destructive">
          <AlertDescription>
            {{ verificationError }}
          </AlertDescription>
        </Alert>
        <Alert v-else-if="!token" variant="info">
          <AlertDescription>
            {{ t('auth.verify_email.instructions') }}
          </AlertDescription>
        </Alert>
      </div>

      <div class="space-y-6">
        <div v-if="!isVerified" class="space-y-2 text-left">
          <Label for="email">
            {{ t('auth.verify_email.resend_label') }}
          </Label>
          <Input
            id="email"
            v-model="emailInput"
            type="email"
            :placeholder="t('auth.form.email_placeholder')"
            :disabled="isResendingVerification"
          />
          <p class="text-xs text-muted-foreground">
            {{ t('auth.verify_email.resend_helper') }}
          </p>
        </div>

        <div v-if="isVerified" class="flex flex-col items-center justify-center gap-3">
          <RotateCwIcon class="size-8 animate-spin opacity-50" />
          <p class="text-xs text-muted-foreground">
            {{ t('auth.verify_email.redirecting_to_login') }}
          </p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button
            type="button"
            variant="default"
            :loading="isResendingVerification"
            :disabled="isVerified || isResendingVerification"
            @click="handleResend"
          >
            {{ t('auth.verify_email.resend_button') }}
          </Button>
          <ButtonLink
            v-if="isVerified"
            type="button"
            variant="outline"
            :to="AuthRoutePaths.login"
          >
            {{ t('auth.verify_email.back_to_login') }}
          </ButtonLink>
          <ButtonLink
            v-else
            type="button"
            variant="outline"
            :to="AuthRoutePaths.login"
          >
            {{ t('auth.verify_email.back_to_login') }}
          </ButtonLink>
        </div>
      </div>
    </div>
  </GuestLayoutCentered>
</template>

