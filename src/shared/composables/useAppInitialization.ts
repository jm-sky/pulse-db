/**
 * App initialization composable
 */

import { computed, watchEffect } from 'vue'
import { useSettingsQuery } from '@/modules/settings/composables/useSettings'
import { useDarkMode } from '@/shared/composables/useDarkMode'
import { useLocale } from '@/shared/i18n'
import type { Settings } from '@/modules/settings/types/settings.type'

export interface AppInitializationState {
  isInitialized: boolean
  error: unknown
  settings?: Settings
}

export function useAppInitialization() {
  const { setLocale } = useLocale()
  const { setDark } = useDarkMode()
  const settingsQuery = useSettingsQuery()

  watchEffect(() => {
    if (settingsQuery.data.value) {
      if (settingsQuery.data.value.locale) {
        setLocale(settingsQuery.data.value.locale)
      }
      if (settingsQuery.data.value.darkMode !== undefined) {
        setDark(settingsQuery.data.value.darkMode)
      }
    }
  })

  const isInitialized = computed(() => !settingsQuery.isPending.value)

  return {
    isInitialized,
    error: settingsQuery.error,
    settings: settingsQuery.data,
    isLoading: settingsQuery.isPending,
    isError: settingsQuery.isError,
  }
}
