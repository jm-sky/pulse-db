// router/publicRoutes.ts
// Configurable route paths for public pages (about, cookies, privacy, terms, contact, etc.)

import type { RouteRecordRaw } from 'vue-router'

export const PublicRoutePaths = {
  landing: '/',
  about: '/about',
  cookies: '/cookies',
  privacy: '/privacy',
  terms: '/terms',
  contact: '/contact',
  notFound: '/:pathMatch(.*)*',
} as const

export const PublicRouteNames = {
  landing: 'landing',
  about: 'about',
  cookies: 'cookies',
  privacy: 'privacy',
  terms: 'terms',
  contact: 'contact',
  notFound: 'not-found',
} as const

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: PublicRoutePaths.landing,
    name: PublicRouteNames.landing,
    component: () => import('@/pages/LandingPage.vue'),
    meta: { title: 'common.pages.landing' },
  },
  {
    path: PublicRoutePaths.about,
    name: PublicRouteNames.about,
    component: () => import('@/pages/AboutPage.vue'),
    meta: { layout: 'authenticated', title: 'common.pages.about' },
  },
  {
    path: PublicRoutePaths.cookies,
    name: PublicRouteNames.cookies,
    component: () => import('@/pages/CookiesPage.vue'),
    meta: { layout: 'authenticated', title: 'common.pages.cookies' },
  },
  {
    path: PublicRoutePaths.privacy,
    name: PublicRouteNames.privacy,
    component: () => import('@/pages/PrivacyPage.vue'),
    meta: { layout: 'authenticated', title: 'common.pages.privacy' },
  },
  {
    path: PublicRoutePaths.terms,
    name: PublicRouteNames.terms,
    component: () => import('@/pages/TermsPage.vue'),
    meta: { layout: 'authenticated', title: 'common.pages.terms' },
  },
  {
    path: PublicRoutePaths.contact,
    name: PublicRouteNames.contact,
    component: () => import('@/pages/ContactPage.vue'),
    meta: { layout: 'authenticated', title: 'common.pages.contact' },
  },
  {
    path: PublicRoutePaths.notFound,
    name: PublicRouteNames.notFound,
    component: () => import('@/pages/NotFoundPage.vue'),
    meta: { layout: 'public', title: 'common.pages.notFound' },
  },
]

