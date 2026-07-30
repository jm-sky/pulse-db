<script setup lang="ts">
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import Input from '@/components/ui/input/Input.vue'
import { useDisableTotp } from '@/modules/auth/composables/useTotp'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

const props = defineProps<{
  service?: ITwoFactorService
}>()

const { t } = useI18n()

const { handleSubmit, setErrors } = useForm({
  initialValues: {
    password: '',
  }
})

const emit = defineEmits<{
  success: []
  cancel: []
}>()

const { mutateAsync: disableTotp, isPending: isDisabling } = useDisableTotp(props.service)

const { handleError } = useHandleError()

const handleDisableTotp = handleSubmit(async (values: { password: string }) => {
  try {
    await disableTotp(values.password)
    toast.success(t('auth.two_factor.totp.disable_success'))
    emit('success')
  } catch (error: unknown) {
    console.error('Disable TOTP error:', error)
    handleError(error, { setErrors })
  }
})
</script>

<template>
  <form class="border p-4 rounded-md shadow-sm space-y-4" @submit="handleDisableTotp">
    <FormField v-slot="{ componentField }" name="password">
      <FormItem>
        <FormLabel required>
          {{ t('auth.password') }}
        </FormLabel>
        <FormControl>
          <Input type="password" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <div class="flex flex-col sm:flex-row gap-4">
      <Button
        type="button"
        variant="outline"
        class="flex-1"
        @click="emit('cancel')"
      >
        {{ t('auth.two_factor.totp.cancel') }}
      </Button>
      <Button
        type="submit"
        variant="destructive"
        class="flex-1"
        :loading="isDisabling"
      >
        {{ t('auth.two_factor.totp.disable') }}
      </Button>
    </div>
  </form>
</template>
