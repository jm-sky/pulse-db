<script setup lang="ts">
import { Activity, Database, Search, Settings } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import UserNav from '@/components/layout/UserNav.vue'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import LogoText from '@/components/ui/LogoText.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRouteNames, AuthRoutePaths } from '@/modules/auth/config/routes'
import { SettingsRoutePaths } from '@/modules/settings/routes'
import { useUser } from '@/modules/user/composables/useUser'
import { UserRoutePaths } from '@/modules/user/routes'
import { PublicRoutePaths } from '@/router/publicRoutes'
import DarkModeToggle from '@/shared/components/DarkModeToggle.vue'
import LocaleToggle from '@/shared/i18n/components/LocaleToggle.vue'

const props = defineProps<{
  explorerOpen: boolean
}>()

const emit = defineEmits<{
  'update:explorerOpen': [value: boolean]
  openCommandPalette: []
}>()

const { t } = useI18n()
const router = useRouter()
const { logout, user: authUser } = useAuth()
const { profile } = useUser()
const user = computed(() => authUser.value ?? profile.value)

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const paletteShortcut = isMac ? '⌘K' : 'Ctrl+K'

function stub() {
  toast.message(t('monitoring.menubar.comingSoon'))
}

async function handleLogout() {
  try {
    await logout()
    toast.success(t('auth.logout_success', 'Logged out successfully'))
    await router.push({ name: AuthRouteNames.login })
  } catch {
    toast.error(t('auth.logout_error', 'Failed to logout'))
  }
}
</script>

<template>
  <header class="flex h-9 shrink-0 items-center gap-1 border-b border-border bg-background px-2 text-sm">
    <RouterLink
      :to="AuthRoutePaths.dashboard"
      class="mr-2 flex items-center gap-1.5 px-1.5 text-foreground hover:opacity-80"
    >
      <Database class="size-4 text-primary" />
      <LogoText class="text-sm font-semibold tracking-tight" />
    </RouterLink>

    <nav class="flex items-center gap-0.5">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="sm" class="h-7 px-2 font-normal">
            {{ t('monitoring.menubar.file') }}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem @click="router.push(SettingsRoutePaths.settings)">
            <Settings class="size-4" />
            {{ t('monitoring.menubar.settings') }}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem @click="stub">
            {{ t('monitoring.menubar.refresh') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="sm" class="h-7 px-2 font-normal">
            {{ t('monitoring.menubar.view') }}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem @click="emit('update:explorerOpen', !props.explorerOpen)">
            {{ t('monitoring.menubar.toggleExplorer') }}
          </DropdownMenuItem>
          <DropdownMenuItem @click="emit('openCommandPalette')">
            {{ t('monitoring.menubar.commandPalette') }}
            <DropdownMenuShortcut>{{ paletteShortcut }}</DropdownMenuShortcut>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="sm" class="h-7 px-2 font-normal">
            {{ t('monitoring.menubar.tools') }}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem disabled>
            <Activity class="size-4" />
            {{ t('monitoring.menubar.comingSoon') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="sm" class="h-7 px-2 font-normal">
            {{ t('monitoring.menubar.help') }}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <DropdownMenuItem @click="router.push(PublicRoutePaths.about)">
            {{ t('monitoring.menubar.about') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </nav>

    <div class="ml-auto flex items-center gap-1">
      <Button
        variant="outline"
        size="sm"
        class="h-7 gap-1.5 px-2 text-muted-foreground"
        @click="emit('openCommandPalette')"
      >
        <Search class="size-3.5" />
        <span class="hidden sm:inline">{{ t('monitoring.menubar.commandPalette') }}</span>
        <kbd class="pointer-events-none hidden h-5 select-none items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:inline-flex">
          {{ paletteShortcut }}
        </kbd>
      </Button>
      <LocaleToggle />
      <DarkModeToggle />
      <UserNav
        :user-name="user?.name ?? t('user.guest')"
        :user-email="user?.email"
        :user-avatar="user?.avatarUrl"
        :core-links="[
          { to: UserRoutePaths.profile, label: t('user.profile.title', 'Profile') },
          { to: SettingsRoutePaths.settings, label: t('settings.page.title', 'Settings') },
        ]"
        @logout="handleLogout"
      />
    </div>
  </header>
</template>
