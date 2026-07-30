import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { settingsService } from '@/modules/settings/services/settingsService'
import {
  settingsMutationRetryFunction,
  settingsQueryKeys,
  settingsRetryFunction
} from '@/modules/settings/utils/queryUtils'
import { useDarkMode } from '@/shared/composables/useDarkMode'
import { useLocale } from '@/shared/i18n'
import type { ISettingsService, Settings, UpdateSettingsData } from '@/modules/settings/types/settings.type'

export function useSettingsQuery(service?: ISettingsService) {
  return useQuery({
    queryKey: settingsQueryKeys.me(),
    queryFn: () => (service ?? settingsService).getSettings(),
    staleTime: 5 * 60 * 1000,
    retry: settingsRetryFunction,
  })
}

export function useUpdateSettings(service?: ISettingsService) {
  const queryClient = useQueryClient()
  const { setLocale } = useLocale()
  const { setDark } = useDarkMode()

  return useMutation({
    mutationFn: (data: UpdateSettingsData) => (service ?? settingsService).updateSettings(data),
    onSuccess: (updated: Settings) => {
      queryClient.setQueryData(settingsQueryKeys.me(), updated)
      // Sync locale via useLocale to ensure LOCALE_STORAGE_KEY is source of truth
      setLocale(updated.locale)
      // Sync darkMode via useDarkMode
      setDark(updated.darkMode)
      void queryClient.invalidateQueries({ queryKey: settingsQueryKeys.me() })
    },
    retry: settingsMutationRetryFunction,
  })
}

export function useSettings(service?: ISettingsService) {
  const queryClient = useQueryClient()

  const settingsQuery = useSettingsQuery(service)
  const updateMutation = useUpdateSettings(service)

  const settings = settingsQuery.data
  const isLoading = settingsQuery.isLoading
  const isError = settingsQuery.isError
  const error = settingsQuery.error

  const refetchSettings = () => queryClient.invalidateQueries({ queryKey: settingsQueryKeys.me() })

  return {
    settingsQuery,
    settings,
    isLoading,
    isError,
    error,
    updateSettings: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    refetchSettings,
  }
}
