<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import GuestLayoutCard from '@/components/layout/GuestLayoutCard.vue'
import Alert from '@/components/ui/alert/Alert.vue'
import AlertDescription from '@/components/ui/alert/AlertDescription.vue'
import GuestLayoutCentered from '@/layouts/GuestLayoutCentered.vue'
import LoginForm from '@/modules/auth/components/LoginForm.vue'
import type { IAuthService } from '@/modules/auth/types/auth.type'

const { t } = useI18n()
const route = useRoute()
const message: string | null = route.meta.message as string | null

const { authService } = defineProps<{
  authService?: IAuthService
  defaultEmail?: string
}>()
</script>

<template>
  <GuestLayoutCentered>
    <template #actions>
      <slot name="actions" />
    </template>

    <GuestLayoutCard :title="t('auth.sign_in_to_account')">
      <template #header-description>
        <p class="mt-2 text-center text-sm text-muted-foreground">
          {{ t('auth.links.or_create_account') }}
          <RouterLink to="/auth/register" class="font-medium text-primary hover:underline">
            {{ t('auth.links.create_new_account') }}
          </RouterLink>
        </p>
      </template>

      <LoginForm :auth-service :default-email />

      <template #footer>
        <RouterLink to="/auth/forgot-password" class="text-sm text-muted-foreground hover:underline">
          {{ t('auth.forgot_password') }}
        </RouterLink>
      </template>
      <template #after>
        <Alert v-if="message" variant="info">
          <AlertDescription>{{ message }}</AlertDescription>
        </Alert>
      </template>
    </GuestLayoutCard>
  </GuestLayoutCentered>
</template>
