<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { PinInput, PinInputGroup, PinInputSlot } from '@/components/ui/pin-input'
import { useVerifyTotpLogin } from '@/modules/auth/composables/useTotp'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { totpVerifySchema } from '@/modules/auth/validation/totp.schema'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

const props = defineProps<{
  service?: ITwoFactorService
  isLogin?: boolean // If true, use login verification endpoint
}>()

const emit = defineEmits<{
  success: [accessToken: string]
}>()

const { t } = useI18n()
const authStore = useAuthStore()
const twoFactorToken = computed(() => authStore.twoFactorToken)

// Use login verification if isLogin is true and we have a 2FA token
const isLoginFlow = computed(() => props.isLogin && !!twoFactorToken.value)
const { mutateAsync: verifyTotpLogin, isPending: isVerifyingLogin } = useVerifyTotpLogin(props.service)
const isVerifying = computed(() => isVerifyingLogin.value)

const pinValue = ref<number[]>([])

const { handleSubmit, setErrors, setFieldValue } = useForm({
  validationSchema: toTypedSchema(totpVerifySchema),
  initialValues: {
    code: '',
  },
})

const onSubmit = async (values: { code: string }) => {
  if (!isLoginFlow.value || !twoFactorToken.value) {
    // This component is only for login flow
    toast.error(t('errors.generic'))
    return
  }

  try {
    // Login flow - use verify-totp-login endpoint
    const result = await verifyTotpLogin({
      code: values.code,
      twoFactorToken: twoFactorToken.value,
    })

    if (result.verified && result.accessToken) {
      emit('success', result.accessToken)
      toast.success(t('auth.two_factor.verification_success'))
    } else {
      setErrors({ code: t('auth.two_factor.totp.invalid_code') })
      toast.error(t('auth.two_factor.totp.invalid_code'))
      // Reset PIN input on error
      pinValue.value = []
    }
  } catch (err: unknown) {
    const errorMessage = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('errors.generic')
    setErrors({ code: errorMessage })
    toast.error(errorMessage)
    // Reset PIN input on error
    pinValue.value = []
    console.error('TOTP verification error:', err)
  }
}

const submitForm = handleSubmit(onSubmit)

// Sync PIN input with form field
const handlePinInput = (value: number[]) => {
  pinValue.value = value
  const code = value.join('')
  setFieldValue('code', code, false)

  // Auto-submit when all 6 digits are entered (after validation)
  if (code.length === 6) {
    // Use nextTick to ensure field value is set before validation
    void nextTick(() => {
      submitForm()
    })
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submitForm">
    <FormField name="code">
      <FormItem>
        <FormLabel class="mx-auto" required>
          {{ t('auth.two_factor.totp.code_label') }}
        </FormLabel>
        <FormControl>
          <PinInput
            v-model="pinValue"
            type="number"
            class="mx-auto"
            :disabled="isVerifying"
            @update:model-value="handlePinInput"
          >
            <PinInputGroup>
              <PinInputSlot
                v-for="index in 6"
                :key="index"
                :index="index - 1"
              />
            </PinInputGroup>
          </PinInput>
        </FormControl>
        <FormMessage />
        <p class="text-sm mx-auto text-muted-foreground">
          {{ t('auth.two_factor.totp.enter_code_help') }}
        </p>
      </FormItem>
    </FormField>

    <Button
      type="submit"
      class="w-full"
      :loading="isVerifying"
    >
      {{ t('auth.two_factor.verify_button') }}
    </Button>
  </form>
</template>
