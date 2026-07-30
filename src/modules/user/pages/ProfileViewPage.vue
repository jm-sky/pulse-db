<script setup lang="ts">
import { Edit, ExternalLink, Mail } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Avatar from '@/components/ui/avatar/Avatar.vue'
import AvatarFallback from '@/components/ui/avatar/AvatarFallback.vue'
import AvatarImage from '@/components/ui/avatar/AvatarImage.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import UserRoleBadge from '@/components/ui/UserRoleBadge.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useSettings } from '@/modules/settings/composables/useSettings'
import { getInitials } from '@/shared/utils/getInitials'
import AuthenticationRequiredAlert from '../components/AuthenticationRequiredAlert.vue'
import { useUser } from '../composables/useUser'
import { UserRoutePaths } from '../routes'

const { t } = useI18n()
const { profile } = useUser()
const { settings } = useSettings()
const { isAuthenticated } = useAuth()

const isProfilePublic = computed(() => settings.value?.profilePublic ?? false)
const publicProfileUrl = computed(() => {
  if (profile.value?.id && isProfilePublic.value) {
    return `/users/${profile.value.id}/public`
  }
  return null
})

// Generate initials from name or email using shared helper
const initials = computed(() => {
  if (profile.value?.name) {
    return getInitials(profile.value.name)
  }
  if (profile.value?.email) {
    return profile.value.email.substring(0, 2).toUpperCase()
  }
  return 'U'
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-1">
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-3xl font-bold tracking-tight">
              {{ t('user.profile.title') }}
            </h1>
          </div>
          <p class="text-sm text-muted-foreground">
            {{ t('user.profile.subtitle') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <ButtonLink
            v-if="publicProfileUrl"
            variant="outline"
            class="flex-1 sm:flex-none"
            :to="publicProfileUrl"
          >
            <ExternalLink class="size-4" />
            {{ t('user.edit.show_public_profile') }}
          </ButtonLink>
          <ButtonLink
            v-if="isAuthenticated"
            variant="outline"
            class="flex-1 sm:flex-none"
            :to="UserRoutePaths.profileEdit"
          >
            <Edit class="size-4" />
            {{ t('user.profile.edit_button') }}
          </ButtonLink>
        </div>
      </div>

      <div v-if="profile" class="bg-card border rounded-lg p-6 space-y-6">
        <div class="flex flex-col sm:flex-row items-center gap-x-6 gap-y-4">
          <Avatar class="size-24 ring-1 ring-border">
            <AvatarImage :src="profile.avatarUrl ?? ''" :alt="profile.name" />
            <AvatarFallback class="bg-muted text-muted-foreground text-2xl font-semibold">
              {{ initials }}
            </AvatarFallback>
          </Avatar>
          <div class="flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h2 class="text-2xl font-semibold">
                {{ profile.name }}
              </h2>
              <UserRoleBadge
                :is-admin="profile.isAdmin"
                :is-owner="profile.isOwner"
                :is-premium="profile.isPremium"
              />
            </div>
            <div class="flex items-center mt-2 text-muted-foreground">
              <Mail class="size-4 mr-2 shrink-0" />
              <span class="break-all">{{ profile.email }}</span>
            </div>
          </div>
        </div>

        <div class="border-t pt-4 space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-1">
              <label class="text-xs uppercase tracking-wide text-muted-foreground">
                {{ t('user.profile.user_id_label') }}
              </label>
              <p class="text-sm font-mono">
                {{ profile.id }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="bg-card border rounded-lg p-6 text-center">
        <p class="text-muted-foreground">
          {{ t('user.profile.no_profile') }}
        </p>
      </div>

      <AuthenticationRequiredAlert v-if="!isAuthenticated" />
    </div>
  </AuthenticatedLayout>
</template>

