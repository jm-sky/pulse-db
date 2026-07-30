<script setup lang="ts">
import { Fingerprint, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePasskeys } from '@/modules/auth/composables/useTwoFactor'
import { useDeletePasskey } from '@/modules/auth/composables/useWebAuthn'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

const props = defineProps<{
  service?: ITwoFactorService
}>()

const { t } = useI18n()
const { data: passkeys, isLoading } = usePasskeys(props.service)
const { mutateAsync: deletePasskey, isPending: isDeleting } = useDeletePasskey(props.service)

const handleDelete = async (passkeyId: string) => {
  if (!confirm(t('auth.two_factor.webauthn.delete_confirm'))) {
    return
  }

  try {
    await deletePasskey(passkeyId)
    toast.success(t('auth.two_factor.webauthn.delete_success'))
  } catch (err) {
    toast.error(t('errors.generic'))
    console.error('Passkey deletion error:', err)
  }
}

const formatDate = (dateString?: string) => {
  if (!dateString) return t('common.never')
  return new Date(dateString).toLocaleDateString()
}
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <Fingerprint class="size-5 shrink-0" />
        <CardTitle class="text-lg sm:text-xl">
          {{ t('auth.two_factor.webauthn.registered_passkeys') }}
        </CardTitle>
      </div>
      <CardDescription>{{ t('auth.two_factor.webauthn.passkeys_description') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="isLoading" class="py-8 text-center text-muted-foreground">
        {{ t('common.loading') }}
      </div>

      <div v-else-if="!passkeys || passkeys.length === 0" class="py-8 text-center text-muted-foreground">
        <Fingerprint class="mx-auto mb-2 size-12 opacity-20" />
        <p>{{ t('auth.two_factor.webauthn.no_passkeys') }}</p>
      </div>

      <template v-else>
        <div class="space-y-3 md:hidden">
          <div
            v-for="passkey in passkeys"
            :key="passkey.id"
            class="space-y-2 rounded-lg border p-3"
          >
            <div class="flex items-start justify-between gap-2">
              <p class="font-medium text-sm">
                {{ passkey.name }}
              </p>
              <Button
                variant="ghost"
                size="icon"
                class="size-9 shrink-0 hover:text-destructive"
                :disabled="isDeleting"
                :aria-label="t('auth.two_factor.webauthn.delete')"
                @click="handleDelete(passkey.id)"
              >
                <Trash2 class="size-4" />
              </Button>
            </div>
            <div class="space-y-1 text-xs text-muted-foreground">
              <p>
                {{ t('auth.two_factor.webauthn.created') }}: {{ formatDate(passkey.createdAt) }}
              </p>
              <p>
                {{ t('auth.two_factor.webauthn.last_used') }}: {{ formatDate(passkey.lastUsedAt) }}
              </p>
            </div>
          </div>
        </div>

        <div class="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{{ t('auth.two_factor.webauthn.name') }}</TableHead>
                <TableHead>{{ t('auth.two_factor.webauthn.created') }}</TableHead>
                <TableHead>{{ t('auth.two_factor.webauthn.last_used') }}</TableHead>
                <TableHead class="text-right">
                  {{ t('common.actions') }}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="passkey in passkeys" :key="passkey.id">
                <TableCell class="font-medium">
                  {{ passkey.name }}
                </TableCell>
                <TableCell>{{ formatDate(passkey.createdAt) }}</TableCell>
                <TableCell>{{ formatDate(passkey.lastUsedAt) }}</TableCell>
                <TableCell class="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    :disabled="isDeleting"
                    :aria-label="t('auth.two_factor.webauthn.delete')"
                    class="hover:text-destructive"
                    @click="handleDelete(passkey.id)"
                  >
                    <Trash2 class="size-4" />
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </template>
    </CardContent>
  </Card>
</template>
