import { adminRoutes } from '@/modules/admin/routes'
import { authRoutes } from '@/modules/auth/config/routes'
import { monitoringRoutes } from '@/modules/monitoring/routes'
import { settingsRoutes } from '@/modules/settings/routes'
import { userRoutes } from '@/modules/user/routes'
import { publicRoutes } from '@/router/publicRoutes'
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  // Landing page (public)
  ...publicRoutes.filter(route => route.name === 'landing'),
  // Domain workspace (desktop shell) — /dashboard redirects to /waits
  ...monitoringRoutes,
  // Other public pages (about, cookies, privacy, terms, contact)
  ...publicRoutes.filter(route => route.name !== 'landing' && route.name !== 'not-found'),
  // Module routes
  ...authRoutes,
  ...adminRoutes,
  ...settingsRoutes,
  ...userRoutes,
  // 404 catch-all route - must be last
  ...publicRoutes.filter(route => route.name === 'not-found'),
]
