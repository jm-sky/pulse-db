<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { Activity, Search, Settings, User } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'
import { SettingsRoutePaths } from '@/modules/settings/routes'
import { UserRoutePaths } from '@/modules/user/routes'

const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const router = useRouter()
const { selectedInstanceId } = useWorkspaceContext()

const keys = useMagicKeys()
const metaK = keys['Meta+K']
const ctrlK = keys['Control+K']

whenever(metaK, () => {
  open.value = !open.value
})
whenever(ctrlK, () => {
  open.value = !open.value
})

async function run(path: string) {
  open.value = false
  await router.push(path)
}

function openQueries() {
  if (selectedInstanceId.value) {
    void run(MonitoringRoutePaths.instanceQueries(selectedInstanceId.value))
    return
  }
  void run(MonitoringRoutePaths.queries)
}
</script>

<template>
  <CommandDialog
    v-model:open="open"
    :title="t('monitoring.command.title')"
    :description="t('monitoring.command.description')"
  >
    <CommandInput :placeholder="t('monitoring.command.placeholder')" />
    <CommandList>
      <CommandEmpty>{{ t('monitoring.command.empty') }}</CommandEmpty>
      <CommandGroup :heading="t('monitoring.command.groupNavigate')">
        <CommandItem value="waits" @select="() => run(MonitoringRoutePaths.waits)">
          <Activity />
          <span>{{ t('monitoring.command.openWaits') }}</span>
        </CommandItem>
        <CommandItem value="queries" @select="() => openQueries()">
          <Search />
          <span>{{ t('monitoring.command.openQueries') }}</span>
        </CommandItem>
        <CommandItem value="settings" @select="() => run(SettingsRoutePaths.settings)">
          <Settings />
          <span>{{ t('monitoring.command.openSettings') }}</span>
        </CommandItem>
        <CommandItem value="profile" @select="() => run(UserRoutePaths.profile)">
          <User />
          <span>{{ t('monitoring.command.openProfile') }}</span>
        </CommandItem>
      </CommandGroup>
      <CommandSeparator />
      <CommandGroup :heading="t('monitoring.command.groupActions')">
        <CommandItem value="palette-hint" disabled>
          <span>{{ t('monitoring.menubar.commandPalette') }}</span>
          <CommandShortcut>⌘K</CommandShortcut>
        </CommandItem>
      </CommandGroup>
    </CommandList>
  </CommandDialog>
</template>
