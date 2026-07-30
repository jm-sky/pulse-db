<script setup lang="ts">
import { Shield } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import GuestLayoutCard from '@/components/layout/GuestLayoutCard.vue'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import GuestLayoutCentered from '@/layouts/GuestLayoutCentered.vue'
import TotpVerifyForm from '@/modules/auth/components/TotpVerifyForm.vue'
import WebAuthnVerifyForm from '@/modules/auth/components/WebAuthnVerifyForm.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRouteNames, AuthRoutePaths } from '@/modules/auth/config/routes'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

const props = defineProps<{
  service?: ITwoFactorService
  methods?: string[] // Available 2FA methods from login response
  preferredMethod?: string | null // Preferred method from login response
}>()

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { logout, isLoggingOut } = useAuth()

// Get 2FA token and methods from store
const twoFactorToken = computed(() => authStore.twoFactorToken)
const twoFactorMethods = computed(() => authStore.twoFactorMethods)
const preferredTwoFactorMethod = computed(() => authStore.preferredTwoFactorMethod)

// Determine available 2FA methods from props or store
// For login flow, methods come from login response and are stored in the store
// For authenticated flow, we would fetch from API (not implemented yet)
const methods = computed(() => {
  // Use props if provided (for testing), otherwise use store
  if (props.methods && props.methods.length > 0) {
    return props.methods
  }
  if (twoFactorMethods.value.length > 0) {
    return twoFactorMethods.value
  }
  // Default to TOTP if not provided
  return ['totp']
})
const hasTOTP = computed(() => methods.value.includes('totp'))
const hasWebAuthn = computed(() => methods.value.includes('webauthn'))

// Get preferred method
const defaultMethod = computed(() => {
  const preferred = props.preferredMethod ?? preferredTwoFactorMethod.value
  if (preferred && methods.value.includes(preferred)) {
    return preferred
  }
  // Fallback to first available method
  return methods.value[0] ?? 'totp'
})

// Check if user has 2FA token, redirect to login if not
onMounted(() => {
  if (!twoFactorToken.value) {
    // No 2FA token - redirect to login
    router.push({
      name: AuthRouteNames.login,
      query: { redirectTo: route.query.redirectTo as string | undefined },
    })
  }
})

const handleVerificationSuccess = async (_accessToken: string) => {
  // Token is already set in store by the verification composable
  // Redirect to dashboard or intended page
  const redirectTo = typeof route.query.redirectTo === 'string' ? route.query.redirectTo : AuthRoutePaths.dashboard
  await router.push(redirectTo)
}

const handleLogout = async () => {
  try {
    await logout()
  } finally {
    await router.push({ name: AuthRouteNames.login })
  }
}
</script>

<template>
  <GuestLayoutCentered>
    <GuestLayoutCard :title="t('auth.two_factor.verify_page.title')">
      <template #icon>
        <Shield :size="24" />
      </template>

      <template #header-description>
        <p class="mt-2 text-center text-sm text-muted-foreground">
          {{ t('auth.two_factor.verify_page.subtitle') }}
        </p>
      </template>

      <!-- Show tabs only if both methods are available -->
      <Tabs v-if="hasTOTP && hasWebAuthn" :default-value="defaultMethod" class="w-full">
        <TabsList class="grid w-full grid-cols-2 mb-4">
          <TabsTrigger value="totp">
            {{ t('auth.two_factor.totp.tab_label') }}
          </TabsTrigger>
          <TabsTrigger value="webauthn">
            {{ t('auth.two_factor.webauthn.tab_label') }}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="totp">
          <TotpVerifyForm :service :is-login="true" @success="handleVerificationSuccess" />
        </TabsContent>

        <TabsContent value="webauthn">
          <WebAuthnVerifyForm :service :is-login="true" @success="handleVerificationSuccess" />
        </TabsContent>
      </Tabs>

      <!-- Show single form if only one method is available -->
      <TotpVerifyForm
        v-else-if="hasTOTP"
        :service
        :is-login="true"
        @success="handleVerificationSuccess"
      />
      <WebAuthnVerifyForm
        v-else-if="hasWebAuthn"
        :service
        :is-login="true"
        @success="handleVerificationSuccess"
      />

      <!-- Fallback if no methods configured (shouldn't happen) -->
      <div v-else class="text-center text-muted-foreground py-4">
        {{ t('auth.two_factor.no_methods_configured') }}
      </div>

      <Button
        type="button"
        variant="outline"
        class="mt-4 w-full"
        :loading="isLoggingOut"
        @click="handleLogout"
      >
        {{ t('auth.logout') }}
      </Button>
    </GuestLayoutCard>
  </GuestLayoutCentered>
</template>
