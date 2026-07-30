<script setup lang="ts">
import { useClipboard } from '@vueuse/core'
import { Check, Copy } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const props = withDefaults(defineProps<{
  qrCode?: string
  qrCodeUri?: string
  secret: string
  embedded?: boolean
}>(), {
  embedded: false,
})

const qrCodeDataUrl = ref<string>('')
const isLoading = ref(true)

onMounted(async () => {
  try {
    if (props.qrCode) {
      qrCodeDataUrl.value = props.qrCode
      isLoading.value = false
      return
    }

    if (props.qrCodeUri) {
      const QRCode = await import('qrcode')
      qrCodeDataUrl.value = await QRCode.default.toDataURL(props.qrCodeUri)
      isLoading.value = false
      return
    }

    isLoading.value = false
  } catch (error) {
    console.error('Error generating QR code:', error)
    toast.error('Failed to generate QR code')
    isLoading.value = false
  }
})

const { t } = useI18n()
const { copy, copied } = useClipboard()

const handleCopySecret = async () => {
  await copy(props.secret)
  toast.success(t('auth.two_factor.totp.secret_copied'))
}
</script>

<template>
  <component :is="embedded ? 'div' : Card">
    <template v-if="!embedded">
      <CardHeader>
        <CardTitle>{{ t('auth.two_factor.totp.scan_qr_code') }}</CardTitle>
        <CardDescription>{{ t('auth.two_factor.totp.scan_qr_code_description') }}</CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="flex justify-center">
          <img
            v-if="!isLoading && qrCodeDataUrl"
            :src="qrCodeDataUrl"
            alt="TOTP QR Code"
            class="max-w-[256px] w-full h-auto"
          />
          <div
            v-else-if="isLoading"
            class="flex aspect-square w-full max-w-64 items-center justify-center rounded bg-muted"
          >
            <p class="text-sm text-muted-foreground">
              Loading QR code...
            </p>
          </div>
          <div
            v-else
            class="flex aspect-square w-full max-w-64 items-center justify-center rounded bg-muted"
          >
            <p class="text-sm text-red-500">
              Failed to load QR code
            </p>
          </div>
        </div>

        <div class="space-y-2">
          <p class="text-sm font-medium">
            {{ t('auth.two_factor.totp.manual_entry') }}
          </p>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <code class="flex-1 rounded bg-muted p-2 text-sm break-all">
              {{ secret }}
            </code>
            <Button
              type="button"
              variant="outline"
              size="icon"
              class="shrink-0 self-end sm:self-auto"
              :aria-label="t('auth.two_factor.totp.copy_secret')"
              @click="handleCopySecret"
            >
              <Check v-if="copied" class="size-4" />
              <Copy v-else class="size-4" />
            </Button>
          </div>
        </div>

        <div class="space-y-1 text-sm text-muted-foreground">
          <p>{{ t('auth.two_factor.totp.scan_instructions') }}</p>
        </div>
      </CardContent>
    </template>

    <div v-else class="space-y-4">
      <div class="flex justify-center">
        <img
          v-if="!isLoading && qrCodeDataUrl"
          :src="qrCodeDataUrl"
          alt="TOTP QR Code"
          class="max-w-[256px] w-full h-auto"
        />
        <div
          v-else-if="isLoading"
          class="flex aspect-square w-full max-w-64 items-center justify-center rounded bg-muted"
        >
          <p class="text-sm text-muted-foreground">
            Loading QR code...
          </p>
        </div>
        <div
          v-else
          class="flex aspect-square w-full max-w-64 items-center justify-center rounded bg-muted"
        >
          <p class="text-sm text-red-500">
            Failed to load QR code
          </p>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-sm font-medium">
          {{ t('auth.two_factor.totp.manual_entry') }}
        </p>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <code class="flex-1 rounded bg-muted p-2 text-sm break-all">
            {{ secret }}
          </code>
          <Button
            type="button"
            variant="outline"
            size="icon"
            class="shrink-0 self-end sm:self-auto"
            :aria-label="t('auth.two_factor.totp.copy_secret')"
            @click="handleCopySecret"
          >
            <Check v-if="copied" class="size-4" />
            <Copy v-else class="size-4" />
          </Button>
        </div>
      </div>

      <div class="space-y-1 text-sm text-muted-foreground">
        <p>{{ t('auth.two_factor.totp.scan_instructions') }}</p>
      </div>
    </div>
  </component>
</template>
