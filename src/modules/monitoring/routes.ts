import type { RouteRecordRaw } from 'vue-router'

export const MonitoringRoutePaths = {
  waits: '/waits',
  queries: '/queries',
  instanceWaits: (instanceId: string) => `/instances/${instanceId}/waits`,
  instanceQueries: (instanceId: string) => `/instances/${instanceId}/queries`,
} as const

export const MonitoringRouteNames = {
  waitsRedirect: 'waits-redirect',
  queriesRedirect: 'queries-redirect',
  instanceWaits: 'instance-waits',
  instanceQueries: 'instance-queries',
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
    path: '/instances/:instanceId/queries',
    name: MonitoringRouteNames.instanceQueries,
    component: () => import('@/modules/monitoring/pages/InstanceQueriesPage.vue'),
    meta: { title: 'monitoring.queries.title', requiresAuth: true },
    props: true,
  },
  {
    path: MonitoringRoutePaths.waits,
    name: MonitoringRouteNames.waitsRedirect,
    component: () => import('@/modules/monitoring/pages/WaitsRedirectPage.vue'),
    meta: { title: 'monitoring.waits.title', requiresAuth: true },
  },
  {
    path: MonitoringRoutePaths.queries,
    name: MonitoringRouteNames.queriesRedirect,
    component: () => import('@/modules/monitoring/pages/QueriesRedirectPage.vue'),
    meta: { title: 'monitoring.queries.title', requiresAuth: true },
  },
  {
    path: '/dashboard',
    redirect: MonitoringRoutePaths.waits,
  },
]
