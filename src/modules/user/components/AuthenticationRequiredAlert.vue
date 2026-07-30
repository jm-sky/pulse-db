<script setup lang="ts">
import { LogIn, UserPlus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Alert from '@/components/ui/alert/Alert.vue'
import AlertDescription from '@/components/ui/alert/AlertDescription.vue'
import AlertTitle from '@/components/ui/alert/AlertTitle.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import { AuthRoutePaths } from '@/modules/auth/config/routes'

const { t } = useI18n()
</script>

<template>
  <Alert variant="primary" class="mx-auto max-w-2xl space-y-3">
    <AlertTitle class="text-center">
      {{ t('user.profile.auth_required_title') }}
    </AlertTitle>
    <AlertDescription class="space-y-3 justify-center">
      <p>{{ t('user.profile.auth_required_message') }}</p>
      <div class="w-full flex flex-col sm:flex-row items-center justify-center gap-2">
        <ButtonLink
          size="sm"
          class="w-full sm:w-auto"
          :to="AuthRoutePaths.login"
        >
          <LogIn class="size-4" />
          {{ t('user.profile.login_button') }}
        </ButtonLink>
        <ButtonLink
          size="sm"
          variant="outline"
          class="w-full sm:w-auto text-foreground"
          :to="AuthRoutePaths.register"
        >
          <UserPlus class="size-4" />
          {{ t('user.profile.register_button') }}
        </ButtonLink>
      </div>
    </AlertDescription>
  </Alert>
</template>

