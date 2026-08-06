<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import DeleteAccountCard from '@/modules/settings/components/DeleteAccountCard.vue'
import OAuthConnectionsCard from '../components/OAuthConnectionsCard.vue'
import PreferencesSettingsCard from '../components/PreferencesSettingsCard.vue'
import SecuritySettingsCard from '../components/SecuritySettingsCard.vue'

const { t } = useI18n()
</script>

<template>
  <DesktopWorkspaceLayout>
    <div class="mx-auto max-w-4xl space-y-6 p-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold tracking-tight">
          {{ t('settings.page.title') }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ t('settings.page.subtitle') }}
        </p>
      </div>

      <div class="space-y-6">
        <PreferencesSettingsCard />
        <SecuritySettingsCard />
        <OAuthConnectionsCard />
        <slot name="after" />
        <DeleteAccountCard />
      </div>
    </div>
  </DesktopWorkspaceLayout>
</template>
