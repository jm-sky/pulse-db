import { useRouter } from 'vue-router'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import type { IAuthService } from '@/modules/auth/types/auth.type'

export function useLogout(service?: IAuthService) {
  const authStore = useAuthStore()
  const router = useRouter()

  async function logout() {
    try {
      await (service ?? authService).logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      authStore.logout()
      await router.push(AuthRoutePaths.login)
    }
  }

  return {
    logout,
  }
}
