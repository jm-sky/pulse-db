import { defineStore } from 'pinia'
import { computed, reactive } from 'vue'
import type { Settings, UpdateSettingsData } from '../types/settings.type'
import { SettingsService } from '../services/settingsService'

export const useSettingsStore = defineStore('settings', () => {
  const state = reactive<Settings>(SettingsService.loadFromStorage())

  function updateSettings(updates: UpdateSettingsData): void {
    const updated = SettingsService.updateSettings(state, updates)
    state.locale = updated.locale
    state.darkMode = updated.darkMode
    state.profilePublic = updated.profilePublic
    state.emailPublic = updated.emailPublic
  }

  function loadFromStorageAction(): void {
    const loaded = SettingsService.loadFromStorage()
    state.locale = loaded.locale
    state.darkMode = loaded.darkMode
    state.profilePublic = loaded.profilePublic
    state.emailPublic = loaded.emailPublic
  }

  return {
    locale: computed(() => state.locale),
    darkMode: computed(() => state.darkMode),
    profilePublic: computed(() => state.profilePublic),
    emailPublic: computed(() => state.emailPublic),
    updateSettings,
    loadFromStorage: loadFromStorageAction,
  }
})
