import { ref } from 'vue'
import { authService } from '@/modules/auth/services/authService'
import { config } from '@/shared/config/config'

export function useOAuth() {
  const isPending = ref(false)
  const isGithubPending = ref(false)
  const error = ref<Error | null>(null)

  const initiateOAuthLogin = async (provider: 'google' | 'facebook' | 'github') => {
    const enabledMap = {
      google: config.oauth.google.enabled,
      facebook: config.oauth.facebook.enabled,
      github: config.oauth.github.enabled,
    }
    if (!enabledMap[provider]) {
      error.value = new Error(`${provider} OAuth not configured`)
      return
    }

    if (provider === 'github') {
      isGithubPending.value = true
    }
    else {
      isPending.value = true
    }
    error.value = null

    try {
      // CSRF `state` is persisted server-side (oauth_state_store) and verified
      // on callback — do not mirror it into sessionStorage (clear-text storage).
      const response = await authService.getOAuthAuthUrl(provider)
      window.location.href = response.authUrl
    }
    catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to initiate login')
      isPending.value = false
      isGithubPending.value = false
    }
  }

  const initiateGoogleLogin = () => initiateOAuthLogin('google')
  const initiateFacebookLogin = () => initiateOAuthLogin('facebook')
  const initiateGithubLogin = () => initiateOAuthLogin('github')

  return {
    error,
    initiateFacebookLogin,
    initiateGithubLogin,
    initiateGoogleLogin,
    isEnabled: config.oauth.google.enabled,
    isFacebookEnabled: config.oauth.facebook.enabled,
    isGithubEnabled: config.oauth.github.enabled,
    isGithubPending,
    isPending,
  }
}
