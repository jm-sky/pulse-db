import type { RouteRecordRaw } from 'vue-router'

export const SettingsRoutePaths = {
  settings: import.meta.env.VITE_SETTINGS_PATH ?? '/settings',
} as const

export const SettingsRouteNames = {
  settings: 'settings',
} as const

export const settingsRoutes: RouteRecordRaw[] = [
  {
    path: SettingsRoutePaths.settings,
    name: SettingsRouteNames.settings,
    component: () => import('@/pages/settings/SettingsPage.vue'),
    meta: { title: 'settings.page.title' },
  },
]
