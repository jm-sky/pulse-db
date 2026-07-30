<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const { t } = useI18n()
</script>

<template>
  <div class="flex min-h-[calc(100vh-4rem)] items-center justify-center p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="text-center">
        <div class="mb-4 text-6xl font-bold text-muted-foreground">
          404
        </div>
        <CardTitle>{{ t('notFound.title') }}</CardTitle>
        <CardDescription>{{ t('notFound.description') }}</CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="space-y-2">
          <p class="text-sm text-muted-foreground">
            {{ t('notFound.suggestions') }}
          </p>
          <div class="flex flex-col gap-2">
            <Button as-child variant="default">
              <RouterLink to="/dashboard">
                {{ t('notFound.goToDashboard') }}
              </RouterLink>
            </Button>
            <Button as-child variant="outline">
              <RouterLink to="/settings">
                {{ t('notFound.goToSettings') }}
              </RouterLink>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
