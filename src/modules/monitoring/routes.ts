import type { RouteRecordRaw } from 'vue-router'

export const MonitoringRoutePaths = {
  waits: '/waits',
} as const

export const MonitoringRouteNames = {
  waits: 'waits',
} as const

export const monitoringRoutes: RouteRecordRaw[] = [
  {
    path: MonitoringRoutePaths.waits,
    name: MonitoringRouteNames.waits,
    component: () => import('@/modules/monitoring/pages/WaitsPage.vue'),
    meta: { title: 'monitoring.waits.title' },
  },
  {
    path: '/dashboard',
    redirect: MonitoringRoutePaths.waits,
  },
]
