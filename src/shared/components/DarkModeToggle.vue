<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import { useUpdateSettings } from '@/modules/settings/composables/useSettings'
import { useDarkMode } from '../composables/useDarkMode'

const { isDark } = useDarkMode()
const updateMutation = useUpdateSettings()
const { t } = useI18n()

const toggle = async () => {
  await updateMutation.mutateAsync({ darkMode: !isDark.value })
}

const tooltipText = computed(() => {
  const mode = isDark.value ? t('common.lightMode') : t('common.darkMode')
  return t('common.toggleDarkMode', { mode })
})

const ariaLabel = computed(() => {
  const mode = isDark.value ? t('common.lightMode') : t('common.darkMode')
  return t('common.toggleDarkMode', { mode })
})
</script>

<template>
  <Button
    v-tooltip.bottom="tooltipText"
    variant="ghost"
    :aria-label="ariaLabel"
    :disabled="updateMutation.isPending.value"
    class="min-w-10"
    @click="toggle"
  >
    <Transition
      enter-from-class="opacity-0 -translate-y-5"
      enter-active-class="absolute transition-all duration-300 ease-in-out"
      enter-to-class="opacity-100 translate-y-0"
      leave-from-class="opacity-100 translate-y-0"
      leave-active-class="absolute transition-all duration-200 ease-in-out"
      leave-to-class="opacity-0 translate-y-5"
    >
      <Sun v-if="isDark" key="sun" class="size-4" />
      <Moon v-else key="moon" class="size-4" />
    </Transition>
  </Button>
</template>
