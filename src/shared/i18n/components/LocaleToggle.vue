<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import { useUpdateSettings } from '@/modules/settings/composables/useSettings'
import { useLocale } from '../composables/useLocale'
import { SUPPORTED_LOCALES } from '../config/i18n'
import type { SupportedLocale } from '@/shared/config/config'

const { nextLocale, currentLocale } = useLocale()
const updateMutation = useUpdateSettings()
const { t } = useI18n()

const toggleLocale = async () => {
  const currentIndex = SUPPORTED_LOCALES.indexOf(currentLocale.value)
  const nextIndex = (currentIndex + 1) % SUPPORTED_LOCALES.length
  const newLocale = SUPPORTED_LOCALES[nextIndex] as SupportedLocale

  if (newLocale) {
    await updateMutation.mutateAsync({ locale: newLocale })
  }
}

const tooltipText = computed(() => {
  return t('common.toggleLanguage', { locale: nextLocale.value.code.toUpperCase() })
})

const ariaLabel = computed(() => {
  return t('common.toggleLanguage', { locale: nextLocale.value.code.toUpperCase() })
})
</script>

<template>
  <Button
    v-tooltip.bottom="tooltipText"
    variant="ghost"
    :aria-label="ariaLabel"
    :disabled="updateMutation.isPending.value"
    class="w-12"
    @click="toggleLocale"
  >
    <Transition
      enter-from-class="opacity-0 -translate-y-5"
      enter-active-class="absolute transition-all duration-300 ease-in-out"
      enter-to-class="opacity-100 translate-y-0"
      leave-from-class="opacity-100 translate-y-0"
      leave-active-class="absolute transition-all duration-200 ease-in-out"
      leave-to-class="opacity-0 translate-y-5"
    >
      <span :key="currentLocale">
        {{ currentLocale.toUpperCase() }}
      </span>
    </Transition>
  </Button>
</template>
