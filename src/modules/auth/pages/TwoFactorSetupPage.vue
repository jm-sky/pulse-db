<script setup lang="ts">
import { CheckCircle2, Shield } from 'lucide-vue-next'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import PasskeyList from '@/modules/auth/components/PasskeyList.vue'
import TotpSetupForm from '@/modules/auth/components/TotpSetupForm.vue'
import WebAuthnRegisterForm from '@/modules/auth/components/WebAuthnRegisterForm.vue'
import { useTotpStatus, useTwoFactorStatus, useWebAuthnStatus } from '@/modules/auth/composables/useTwoFactor'
import { SettingsRoutePaths } from '@/modules/settings/routes'
import DisableTotpDialog from '../components/DisableTotpDialog.vue'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

const props = defineProps<{
  service?: ITwoFactorService
}>()

const { t } = useI18n()

const isDisableTotpDialogOpen = ref(false)

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const { data: twoFactorStatus } = useTwoFactorStatus(props.service)
const { data: totpStatus, refetch: refetchTotpStatus } = useTotpStatus(props.service)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const { data: webauthnStatus, refetch: refetchWebAuthnStatus } = useWebAuthnStatus(props.service)

const showTotpSetup = ref(false)
const showPasskeyRegister = ref(false)

const handleTotpSetupSuccess = async () => {
  showTotpSetup.value = false
  await refetchTotpStatus()
}

const handlePasskeyRegisterSuccess = async () => {
  showPasskeyRegister.value = false
  await refetchWebAuthnStatus()
}

const handleDisableTotpSuccess = async () => {
  isDisableTotpDialogOpen.value = false
  await refetchTotpStatus()
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="max-w-2xl mx-auto space-y-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 flex-wrap">
          <Shield class="size-6 sm:size-7 shrink-0" />
          <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">
            {{ t('auth.two_factor.title') }}
          </h1>
        </div>
        <p class="text-sm text-muted-foreground">
          {{ t('auth.two_factor.subtitle') }}
        </p>
      </div>

      <Tabs default-value="totp" class="w-full">
        <TabsList class="grid h-auto w-full grid-cols-2">
          <TabsTrigger
            value="totp"
            class="whitespace-normal py-2 text-xs leading-tight sm:text-sm"
          >
            {{ t('auth.two_factor.totp.tab_label') }}
          </TabsTrigger>
          <TabsTrigger
            value="webauthn"
            class="whitespace-normal py-2 text-xs leading-tight sm:text-sm"
          >
            {{ t('auth.two_factor.webauthn.tab_label') }}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="totp" class="space-y-4">
          <Card v-if="totpStatus?.enabled">
            <CardHeader>
              <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div class="flex items-center gap-2">
                  <CheckCircle2 class="size-5 shrink-0 text-success" />
                  <CardTitle class="text-lg sm:text-xl">
                    {{ t('auth.two_factor.totp.enabled') }}
                  </CardTitle>
                </div>
                <Button
                  v-if="!isDisableTotpDialogOpen"
                  variant="destructive"
                  size="sm"
                  class="w-full sm:w-auto"
                  @click="isDisableTotpDialogOpen = true"
                >
                  {{ t('auth.two_factor.totp.disable') }}
                </Button>
                <Button
                  v-else
                  variant="outline"
                  size="sm"
                  class="w-full sm:w-auto"
                  @click="isDisableTotpDialogOpen = false"
                >
                  {{ t('auth.two_factor.totp.cancel') }}
                </Button>
              </div>
              <CardDescription>{{ t('auth.two_factor.totp.enabled_description') }}</CardDescription>
              <DisableTotpDialog
                v-if="isDisableTotpDialogOpen"
                :service
                class="mt-3"
                @success="handleDisableTotpSuccess"
                @cancel="isDisableTotpDialogOpen = false"
              />
            </CardHeader>
          </Card>

          <div v-if="!totpStatus?.enabled">
            <TotpSetupForm v-if="showTotpSetup" :service @success="handleTotpSetupSuccess" />
            <Card v-else>
              <CardHeader>
                <CardTitle>{{ t('auth.two_factor.totp.title') }}</CardTitle>
                <CardDescription>{{ t('auth.two_factor.totp.description') }}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button class="w-full sm:w-auto" @click="showTotpSetup = true">
                  {{ t('auth.two_factor.totp.setup') }}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="webauthn" class="space-y-4">
          <PasskeyList :service />

          <div v-if="showPasskeyRegister">
            <WebAuthnRegisterForm :service @success="handlePasskeyRegisterSuccess" />
          </div>
          <Button v-else class="w-full" @click="showPasskeyRegister = true">
            {{ t('auth.two_factor.webauthn.add_passkey') }}
          </Button>
        </TabsContent>
      </Tabs>

      <div class="flex justify-start">
        <ButtonLink variant="outline" class="w-full sm:w-auto" :to="SettingsRoutePaths.settings">
          {{ t('common.back') }}
        </ButtonLink>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
