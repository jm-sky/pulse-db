<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Link2, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { oauthService } from '@/modules/auth/services/oauthService'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { OAuthConnection } from '@/modules/auth/services/oauthService'

const { t } = useI18n()
const { isAuthenticated } = useAuth()
const { handleError } = useHandleError()
const queryClient = useQueryClient()

// Query to fetch OAuth connections
const { data: connections, isLoading } = useQuery<OAuthConnection[]>({
  queryKey: ['oauth-connections'],
  queryFn: () => oauthService.getConnections(),
  enabled: isAuthenticated.value,
  staleTime: 5 * 60 * 1000, // 5 minutes
})

// Mutation to delete OAuth connection
const deleteConnectionMutation = useMutation({
  mutationFn: (provider: string) => oauthService.deleteConnection(provider),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['oauth-connections'] })
    toast.success(t('settings.oauth.connection.deleted'))
  },
  onError: (error: unknown) => {
    handleError(error)
  },
})

const handleDelete = async (provider: string) => {
  if (confirm(t('settings.oauth.connection.confirm_delete', { provider }))) {
    await deleteConnectionMutation.mutateAsync(provider)
  }
}

const getProviderName = (provider: string): string => {
  const providerNames: Record<string, string> = {
    google: t('settings.oauth.providers.google'),
    facebook: t('settings.oauth.providers.facebook'),
  }
  return providerNames[provider] || provider
}

const hasConnections = computed(() => {
  return connections.value && connections.value.length > 0
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <Link2 :size="20" />
        <CardTitle>{{ t('settings.oauth.title') }}</CardTitle>
      </div>
      <CardDescription>{{ t('settings.oauth.description') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="!isAuthenticated" class="text-sm text-muted-foreground py-4">
        {{ t('settings.oauth.login_required') }}
      </div>

      <div v-else-if="isLoading" class="space-y-2">
        <div class="h-4 w-3/4 bg-muted rounded animate-pulse" />
        <div class="h-4 w-1/2 bg-muted rounded animate-pulse" />
      </div>

      <div v-else-if="!hasConnections" class="text-sm text-muted-foreground py-4">
        {{ t('settings.oauth.no_connections') }}
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="connection in connections"
          :key="connection.id"
          class="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
        >
          <div class="flex items-center gap-3 flex-1">
            <div class="flex-1">
              <p class="font-medium text-sm">
                {{ getProviderName(connection.provider) }}
              </p>
              <p v-if="connection.email" class="text-xs text-muted-foreground">
                {{ connection.email }}
              </p>
              <p v-else class="text-xs text-muted-foreground">
                {{ t('settings.oauth.connection.linked') }}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              :disabled="deleteConnectionMutation.isPending.value"
              @click="handleDelete(connection.provider)"
            >
              <Trash2 class="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>


