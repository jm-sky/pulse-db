<script setup lang="ts">
import { MoreHorizontal, Shield, Trash2, User, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import DataTable from '@/components/data-table/DataTable.vue'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import TableEmptyDecorated from '@/components/ui/table/TableEmptyDecorated.vue'
import UserRoleBadge from '@/components/ui/UserRoleBadge.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IAdminUser } from '../types/admin.types'
import type { TUserRole } from '../types/admin.types'
import { adminApiService } from '../services/adminApiService'
import type { ColumnDef } from '@tanstack/vue-table'

const { t } = useI18n()
const { handleError } = useHandleError()
const users = ref<IAdminUser[]>([])
const loading = ref(false)

// Load users
async function loadUsers() {
  loading.value = true
  try {
    users.value = await adminApiService.getUsers(0, 1000)
  } catch (error) {
    console.error('Failed to load users:', error)
    handleError(error, { fallbackMessage: t('admin.users.loadError', 'Failed to load users') })
  } finally {
    loading.value = false
  }
}

// Change user role
async function changeUserRole(user: IAdminUser, newRole: TUserRole) {
  const roleName = t(`admin.users.roles.${newRole}`, newRole)
  const action = t('admin.users.changeRole.action', { role: roleName }, `change role to ${roleName}`)

  if (!confirm(t('admin.users.changeRole.confirm', { action }, `Are you sure you want to ${action}?`))) {
    return
  }

  try {
    await adminApiService.updateUser(user.id, { role: newRole })
    toast.success(
      t('admin.users.changeRole.success', { role: roleName }, `User role changed to ${roleName}`),
    )
    await loadUsers()
  } catch (error) {
    console.error('Failed to change user role:', error)
    handleError(error, { fallbackMessage: t('admin.users.changeRole.error', 'Failed to change user role') })
  }
}

// Delete user
async function deleteUser(userId: string) {
  if (!confirm(t('admin.users.deleteConfirm', 'Are you sure you want to delete this user?'))) {
    return
  }

  try {
    await adminApiService.deleteUser(userId)
    toast.success(t('admin.users.deleteSuccess', 'User deleted successfully'))
    await loadUsers()
  } catch (error) {
    console.error('Failed to delete user:', error)
    handleError(error, { fallbackMessage: t('admin.users.deleteError', 'Failed to delete user') })
  }
}

// Columns
const columns = computed<ColumnDef<IAdminUser>[]>(() => [
  {
    id: 'name',
    accessorKey: 'name',
    header: () => t('admin.users.columns.name', 'Name'),
    enableSorting: true,
  },
  {
    id: 'email',
    accessorKey: 'email',
    header: () => t('admin.users.columns.email', 'Email'),
    enableSorting: true,
  },
  {
    id: 'isAdmin',
    accessorKey: 'isAdmin',
    header: () => t('admin.users.columns.role', 'Role'),
    enableSorting: true,
  },
  {
    id: 'isActive',
    accessorKey: 'isActive',
    header: () => t('admin.users.columns.isActive', 'Active'),
    enableSorting: true,
  },
  {
    id: 'isEmailVerified',
    accessorKey: 'isEmailVerified',
    header: () => t('admin.users.columns.isEmailVerified', 'Verified'),
    enableSorting: true,
  },
  {
    id: 'createdAt',
    accessorKey: 'createdAt',
    header: () => t('admin.users.columns.createdAt', 'Created'),
    enableSorting: true,
  },
  {
    id: 'actions',
    header: () => t('admin.users.columns.actions', 'Actions'),
    enableSorting: false,
    meta: {
      pinned: 'right',
    },
  },
])

// Global filter function
const globalFilterFn = (row: IAdminUser, filterValue: string) => {
  const query = filterValue.toLowerCase()
  return (
    row.name.toLowerCase().includes(query) ||
    row.email.toLowerCase().includes(query)
  )
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <!-- Header -->
      <CommonPageHeader
        :icon="Users"
        :label="t('admin.users.title', 'Users Management')"
        :description="t('admin.users.subtitle', 'Manage user accounts and permissions')"
      />

      <!-- Table -->
      <DataTable
        :loading="loading"
        :columns="columns"
        :data="users"
        :search-placeholder="t('admin.users.search', 'Search users...')"
        :global-filter-fn="globalFilterFn"
        :enable-sorting="true"
        :enable-filtering="true"
        :enable-pagination="true"
        :initial-page-size="20"
      >
        <template #name="{ row }">
          <div class="flex items-center gap-2">
            <div
              v-if="row.original.avatarUrl"
              class="size-8 rounded-full bg-cover bg-center"
              :style="{ backgroundImage: `url(${row.original.avatarUrl})` }"
            />
            <div
              v-else
              class="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-semibold text-sm"
            >
              {{ row.original.name.charAt(0).toUpperCase() }}
            </div>
            <span class="font-medium">{{ row.original.name }}</span>
          </div>
        </template>

        <template #email="{ row }">
          <span class="text-muted-foreground">{{ row.original.email }}</span>
        </template>

        <template #isAdmin="{ row }">
          <UserRoleBadge
            :is-admin="row.original.isAdmin"
            :is-owner="row.original.isOwner"
            :show-icon="false"
          />
          <Badge v-if="!row.original.isAdmin && !row.original.isOwner" variant="secondary">
            {{ t('admin.users.user', 'User') }}
          </Badge>
        </template>

        <template #isActive="{ row }">
          <Badge v-if="row.original.isActive" variant="default">
            {{ t('admin.users.active', 'Active') }}
          </Badge>
          <Badge v-else variant="secondary">
            {{ t('admin.users.inactive', 'Inactive') }}
          </Badge>
        </template>

        <template #isEmailVerified="{ row }">
          <Badge v-if="row.original.isEmailVerified" variant="default">
            {{ t('admin.users.verified', 'Verified') }}
          </Badge>
          <Badge v-else variant="destructive">
            {{ t('admin.users.unverified', 'Unverified') }}
          </Badge>
        </template>

        <template #createdAt="{ row }">
          <span class="text-sm text-muted-foreground">
            {{ new Date(row.original.createdAt).toLocaleDateString() }}
          </span>
        </template>

        <template #actions="{ row }">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="sm">
                <MoreHorizontal class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <!-- Make User - disabled for Owner users or if already a regular user -->
              <DropdownMenuItem
                :disabled="row.original.isOwner || !row.original.isAdmin"
                @click="changeUserRole(row.original, 'user')"
              >
                <User class="size-4" />
                <span>{{ t('admin.users.makeUser', 'Make User') }}</span>
              </DropdownMenuItem>
              <!-- Make Admin - disabled for Owner users or if already admin -->
              <DropdownMenuItem
                :disabled="row.original.isOwner || row.original.isAdmin"
                @click="changeUserRole(row.original, 'admin')"
              >
                <Shield class="size-4" />
                <span>{{ t('admin.users.makeAdmin', 'Make Admin') }}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <!-- Delete - disabled for Owner and Admin users -->
              <DropdownMenuItem
                :disabled="row.original.isOwner || row.original.isAdmin"
                class="text-destructive focus:text-destructive"
                @click="deleteUser(row.original.id)"
              >
                <Trash2 class="size-4" />
                <span>{{ t('admin.users.delete', 'Delete') }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </template>

        <template #empty>
          <TableEmptyDecorated
            :colspan="columns.length"
            :title="t('admin.users.empty', 'No users found')"
            :description="t('admin.users.emptyDescription', 'No users match your search criteria.')"
          />
        </template>
      </DataTable>
    </div>
  </AuthenticatedLayout>
</template>
