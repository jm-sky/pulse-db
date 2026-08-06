import type { RouteRecordRaw } from 'vue-router'

export const MonitoringRoutePaths = {
  waits: '/waits',
  queries: '/queries',
  indexes: '/indexes',
  instance: '/instance',
  instanceWaits: (instanceId: string) => `/instances/${instanceId}/waits`,
  instanceQueries: (instanceId: string) => `/instances/${instanceId}/queries`,
  instanceIndexes: (instanceId: string) => `/instances/${instanceId}/indexes`,
  instanceDetail: (instanceId: string) => `/instances/${instanceId}/instance`,
} as const

export const MonitoringRouteNames = {
  waitsRedirect: 'waits-redirect',
  queriesRedirect: 'queries-redirect',
  indexesRedirect: 'indexes-redirect',
  instanceRedirect: 'instance-redirect',
  instanceWaits: 'instance-waits',
  instanceQueries: 'instance-queries',
  instanceIndexes: 'instance-indexes',
  instanceDetail: 'instance-detail',
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
    path: '/instances/:instanceId/indexes',
    name: MonitoringRouteNames.instanceIndexes,
    component: () => import('@/modules/monitoring/pages/InstanceIndexesPage.vue'),
    meta: { title: 'monitoring.indexes.title', requiresAuth: true },
    props: true,
  },
  {
    path: '/instances/:instanceId/instance',
    name: MonitoringRouteNames.instanceDetail,
    component: () => import('@/modules/monitoring/pages/InstanceDetailPage.vue'),
    meta: { title: 'monitoring.instance.title', requiresAuth: true },
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
    path: MonitoringRoutePaths.indexes,
    name: MonitoringRouteNames.indexesRedirect,
    component: () => import('@/modules/monitoring/pages/IndexesRedirectPage.vue'),
    meta: { title: 'monitoring.indexes.title', requiresAuth: true },
  },
  {
    path: MonitoringRoutePaths.instance,
    name: MonitoringRouteNames.instanceRedirect,
    component: () => import('@/modules/monitoring/pages/InstanceRedirectPage.vue'),
    meta: { title: 'monitoring.instance.title', requiresAuth: true },
  },
  {
    path: '/dashboard',
    redirect: MonitoringRoutePaths.waits,
  },
]
