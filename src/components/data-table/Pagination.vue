<script setup lang="ts">
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface Props {
  page: number
  pageSize: number
  total: number
  pageSizeOptions?: number[]
}

const { t } = useI18n()

const props = withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [10, 20, 30, 40, 50, 100, 500],
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [pageSize: number]
}>()

const totalPages = computed<number>(() => Math.ceil(props.total / props.pageSize))
const canPreviousPage = computed<boolean>(() => props.page > 1)
const canNextPage = computed<boolean>(() => props.page < totalPages.value)

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    emit('update:page', page)
  }
}

const setPageSize = (size: number) => {
  emit('update:pageSize', size)
  // Reset to first page when changing page size
  emit('update:page', 1)
}
</script>

<template>
  <div class="flex items-center justify-between flex-wrap gap-2 md:gap-0 px-2">
    <div class="flex-1 text-sm text-muted-foreground">
      {{ t('common.pagination.totalRows', { total }) }}
    </div>
    <div class="flex items-center justify-center md:justify-start flex-wrap gap-2 md:gap-x-6 lg:gap-x-8">
      <div class="flex items-center gap-x-2">
        <p class="text-sm font-medium">
          {{ t('common.pagination.rowsPerPage') }}
        </p>
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button
              variant="outline"
              class="h-8 w-[70px]"
              :aria-label="t('common.pagination.rowsPerPageValue', { count: pageSize })"
            >
              {{ pageSize }}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              v-for="size in pageSizeOptions"
              :key="size"
              @click="setPageSize(size)"
            >
              {{ size }}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div class="flex w-[100px] items-center justify-center text-sm font-medium">
        {{ t('common.pagination.page') }} {{ page }} {{ t('common.pagination.of') }} {{ totalPages }}
      </div>
      <div class="flex items-center space-x-2">
        <Button
          variant="outline"
          class="hidden size-8 p-0 lg:flex"
          :disabled="!canPreviousPage"
          @click="goToPage(1)"
        >
          <span class="sr-only">{{ t('common.pagination.goToFirstPage') }}</span>
          <ChevronsLeft class="size-4" />
        </Button>
        <Button
          variant="outline"
          class="size-8 p-0"
          :disabled="!canPreviousPage"
          @click="goToPage(page - 1)"
        >
          <span class="sr-only">{{ t('common.pagination.goToPreviousPage') }}</span>
          <ChevronLeft class="size-4" />
        </Button>
        <Button
          variant="outline"
          class="size-8 p-0"
          :disabled="!canNextPage"
          @click="goToPage(page + 1)"
        >
          <span class="sr-only">{{ t('common.pagination.goToNextPage') }}</span>
          <ChevronRight class="size-4" />
        </Button>
        <Button
          variant="outline"
          class="hidden size-8 p-0 lg:flex"
          :disabled="!canNextPage"
          @click="goToPage(totalPages)"
        >
          <span class="sr-only">{{ t('common.pagination.goToLastPage') }}</span>
          <ChevronsRight class="size-4" />
        </Button>
      </div>
    </div>
  </div>
</template>
