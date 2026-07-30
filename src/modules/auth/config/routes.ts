// modules/auth/config/routes.ts
// Configurable route paths for auth module
// This allows the auth module to be used in different apps with different route structures

import type { RouteRecordRaw } from 'vue-router'

export const AUTH_BASE_PATH = import.meta.env.VITE_AUTH_BASE_PATH ?? '/auth'

export const AuthRoutePaths = {
  login: import.meta.env.VITE_AUTH_LOGIN_PATH ?? `${AUTH_BASE_PATH}/login`,
  register: import.meta.env.VITE_AUTH_REGISTER_PATH ?? `${AUTH_BASE_PATH}/register`,
  forgotPassword: import.meta.env.VITE_AUTH_FORGOT_PASSWORD_PATH ?? `${AUTH_BASE_PATH}/forgot-password`,
  resetPassword: import.meta.env.VITE_AUTH_RESET_PASSWORD_PATH ?? `${AUTH_BASE_PATH}/reset-password`,
  changePassword: import.meta.env.VITE_AUTH_CHANGE_PASSWORD_PATH ?? `${AUTH_BASE_PATH}/change-password`,
  twoFactorSetup: import.meta.env.VITE_AUTH_TWO_FACTOR_SETUP_PATH ?? `${AUTH_BASE_PATH}/2fa/setup`,
  twoFactorVerify: import.meta.env.VITE_AUTH_TWO_FACTOR_VERIFY_PATH ?? `${AUTH_BASE_PATH}/2fa/verify`,
  verifyEmail: import.meta.env.VITE_AUTH_VERIFY_EMAIL_PATH ?? `${AUTH_BASE_PATH}/verify-email`,
  oauthCallback: import.meta.env.VITE_AUTH_OAUTH_CALLBACK_PATH ?? `${AUTH_BASE_PATH}/callback/:provider`,
  dashboard: import.meta.env.VITE_AUTH_DASHBOARD_PATH ?? '/dashboard',
} as const

// Named route versions (when using Vue Router named routes)
export const AuthRouteNames = {
  login: 'Login',
  register: 'Register',
  forgotPassword: 'ForgotPassword',
  resetPassword: 'ResetPassword',
  changePassword: 'ChangePassword',
  twoFactorSetup: 'TwoFactorSetup',
  twoFactorVerify: 'TwoFactorVerify',
  verifyEmail: 'VerifyEmail',
  oauthCallback: 'OAuthCallback',
  dashboard: 'Dashboard',
} as const

export const authRoutes: RouteRecordRaw[] = [
  {
    path: AuthRoutePaths.login,
    name: AuthRouteNames.login,
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { title: 'auth.pages.login' },
  },
  {
    path: AuthRoutePaths.register,
    name: AuthRouteNames.register,
    component: () => import('@/modules/auth/pages/RegisterPage.vue'),
    meta: { title: 'auth.pages.register' },
  },
  {
    path: AuthRoutePaths.forgotPassword,
    name: AuthRouteNames.forgotPassword,
    component: () => import('@/modules/auth/pages/ForgotPasswordPage.vue'),
    meta: { title: 'auth.forgot_password_page.title' },
  },
  {
    path: AuthRoutePaths.resetPassword,
    name: AuthRouteNames.resetPassword,
    component: () => import('@/modules/auth/pages/ResetPasswordPage.vue'),
    meta: { title: 'auth.reset_password_page.title' },
  },
  {
    path: AuthRoutePaths.changePassword,
    name: AuthRouteNames.changePassword,
    component: () => import('@/modules/auth/pages/ChangePasswordPage.vue'),
    meta: { title: 'auth.change_password_page.title' },
  },
  {
    path: AuthRoutePaths.twoFactorSetup,
    name: AuthRouteNames.twoFactorSetup,
    meta: { requiresAuth: true, title: 'auth.two_factor.setup.title' },
    component: () => import('@/modules/auth/pages/TwoFactorSetupPage.vue'),
  },
  {
    path: AuthRoutePaths.twoFactorVerify,
    name: AuthRouteNames.twoFactorVerify,
    // Note: This route does NOT require auth (requiresAuth: false)
    // because users in 2FA flow have twoFactorToken but no accessToken
    meta: { requiresAuth: false, title: 'auth.two_factor.verify.title' },
    component: () => import('@/modules/auth/pages/TwoFactorVerifyPage.vue'),
  },
  {
    path: AuthRoutePaths.verifyEmail,
    name: AuthRouteNames.verifyEmail,
    component: () => import('@/modules/auth/pages/VerifyEmailPage.vue'),
    meta: { title: 'auth.pages.verifyEmail' },
  },
  {
    path: AuthRoutePaths.oauthCallback,
    name: AuthRouteNames.oauthCallback,
    component: () => import('@/modules/auth/pages/OAuthCallbackPage.vue'),
    meta: { title: 'auth.pages.oauthCallback' },
  },
]
