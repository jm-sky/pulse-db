import { adminRoutes } from '@/modules/admin/routes'
import { AuthRouteNames, AuthRoutePaths, authRoutes } from '@/modules/auth/config/routes'
import { settingsRoutes } from '@/modules/settings/routes'
import { userRoutes } from '@/modules/user/routes'
import { publicRoutes } from '@/router/publicRoutes'
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  // Landing page (public)
  ...publicRoutes.filter(route => route.name === 'landing'),
  // Dashboard stub (domain modules come later)
  {
    path: AuthRoutePaths.dashboard,
    name: AuthRouteNames.dashboard,
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { layout: 'authenticated', title: 'navigation.dashboard' },
  },
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
