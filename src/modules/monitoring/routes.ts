import type { RouteRecordRaw } from 'vue-router'

export const MonitoringRoutePaths = {
  waits: '/waits',
  instanceWaits: (instanceId: string) => `/instances/${instanceId}/waits`,
} as const

export const MonitoringRouteNames = {
  waitsRedirect: 'waits-redirect',
  instanceWaits: 'instance-waits',
} as const

export const monitoringRoutes: RouteRecordRaw[] = [
  {
    path: '/instances/:instanceId/waits',
    name: MonitoringRouteNames.instanceWaits,
    component: () => import('@/modules/monitoring/pages/InstanceWaitsPage.vue'),
    meta: { title: 'monitoring.waits.title', requiresAuth: true },
    props: true,
  },
  {
    path: MonitoringRoutePaths.waits,
    name: MonitoringRouteNames.waitsRedirect,
    component: () => import('@/modules/monitoring/pages/WaitsRedirectPage.vue'),
    meta: { title: 'monitoring.waits.title', requiresAuth: true },
  },
  {
    path: '/dashboard',
    redirect: MonitoringRoutePaths.waits,
  },
]
