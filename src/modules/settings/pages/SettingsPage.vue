<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import DeleteAccountCard from '@/modules/settings/components/DeleteAccountCard.vue'
import OAuthConnectionsCard from '../components/OAuthConnectionsCard.vue'
import PreferencesSettingsCard from '../components/PreferencesSettingsCard.vue'
import SecuritySettingsCard from '../components/SecuritySettingsCard.vue'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="max-w-4xl mx-auto space-y-6">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('settings.page.title') }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ t('settings.page.subtitle') }}
        </p>
      </div>

      <div class="space-y-6">
        <!-- Core Preferences Settings -->
        <PreferencesSettingsCard />

        <!-- Security Settings (2FA) -->
        <SecuritySettingsCard />

        <!-- OAuth Connections -->
        <OAuthConnectionsCard />

        <!-- Additional Settings from other modules (via slot) -->
        <slot name="after" />

        <DeleteAccountCard />
      </div>
    </div>
  </AuthenticatedLayout>
</template>

