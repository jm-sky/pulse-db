<script setup lang="ts">
import { Check, Copy, Database } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'

const { t } = useI18n()
const copied = ref(false)

const aiContextMarkdown = computed(() => {
  return `# PulseDB - AI Context

## Overview
PulseDB is a self-hosted tool for database performance diagnostics and optimization.
It targets PostgreSQL and Microsoft SQL Server first, with an API-first architecture
so Web UI, CLI, and MCP are clients of the same API.

## Product principles
- Self-hosted and open (AGPLv3)
- Agentless collection in the first version (direct connections to monitored databases)
- Own history store for queries, waits, plans, and index insights
- AI is optional — the product must work fully without AI
- Auth foundation: users, password login, roles/permissions (OAuth/2FA available in platform, not MVP-critical)

## Planned diagnostic scope (MVP direction)
- Query performance history and execution stats
- Wait analysis
- Execution plans
- Index analysis

## Technical stack
### Frontend
- Vue 3.5+ / TypeScript / Pinia / Vue Router
- Tailwind CSS v4 + shadcn-vue
- TanStack Query, vee-validate + zod, vue-i18n

### Backend
- FastAPI (Python, async)
- PostgreSQL + SQLAlchemy async
- JWT auth, Redis, modular FastAPI layout
`
})

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(aiContextMarkdown.value)
    copied.value = true
    toast.success(t('aiContext.copied', 'Context copied to clipboard'))
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    toast.error(t('common.error'))
    console.error('Error copying to clipboard:', error)
  }
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-8">
      <div class="space-y-2">
        <div class="flex items-center gap-3">
          <div class="rounded-full bg-primary/10 p-3">
            <Database class="size-8 text-primary" />
          </div>
          <div>
            <h1 class="text-3xl font-bold tracking-tight">
              {{ t('about.title') }}
            </h1>
            <p class="text-muted-foreground">
              {{ t('about.subtitle') }}
            </p>
          </div>
        </div>
      </div>

      <nav class="flex flex-row flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <a href="#overview" class="text-primary hover:underline">
          {{ t('about.overview.title') }}
        </a>
        <span>|</span>
        <a href="#capabilities" class="text-primary hover:underline">
          {{ t('about.capabilities.title') }}
        </a>
        <span>|</span>
        <a href="#core-features" class="text-primary hover:underline">
          {{ t('about.coreFeatures.title') }}
        </a>
        <span>|</span>
        <a href="#platform" class="text-primary hover:underline">
          {{ t('about.platform.title') }}
        </a>
        <span>|</span>
        <a href="#technical-stack" class="text-primary hover:underline">
          {{ t('about.technical.title') }}
        </a>
        <span>|</span>
        <a href="#ai-context" class="text-primary hover:underline">
          {{ t('aiContext.title') }}
        </a>
      </nav>

      <section id="overview" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.overview.title') }}
        </h2>
        <p class="text-muted-foreground">
          {{ t('about.overview.description') }}
        </p>
      </section>

      <section id="capabilities" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.capabilities.title') }}
        </h2>
        <ul class="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{{ t('about.capabilities.multiEngine') }}</li>
          <li>{{ t('about.capabilities.apiFirst') }}</li>
          <li>{{ t('about.capabilities.selfHosted') }}</li>
          <li>{{ t('about.capabilities.history') }}</li>
          <li>{{ t('about.capabilities.aiOptional') }}</li>
        </ul>
      </section>

      <section id="core-features" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.coreFeatures.title') }}
        </h2>
        <ul class="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{{ t('about.coreFeatures.queries') }}</li>
          <li>{{ t('about.coreFeatures.waits') }}</li>
          <li>{{ t('about.coreFeatures.plans') }}</li>
          <li>{{ t('about.coreFeatures.indexes') }}</li>
          <li>{{ t('about.coreFeatures.agentless') }}</li>
        </ul>
      </section>

      <section id="platform" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.platform.title') }}
        </h2>
        <ul class="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{{ t('about.platform.auth') }}</li>
          <li>{{ t('about.platform.users') }}</li>
          <li>{{ t('about.platform.i18n') }}</li>
          <li>{{ t('about.platform.theming') }}</li>
        </ul>
      </section>

      <section id="technical-stack" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.technical.title') }}
        </h2>
        <div class="space-y-4">
          <div class="space-y-2">
            <h3 class="text-xl font-semibold">
              {{ t('about.technical.frontend.title') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>Vue 3.5+ with TypeScript & Composition API</li>
              <li>Pinia, Vue Router, TanStack Query</li>
              <li>Tailwind CSS v4 + shadcn-vue</li>
              <li>vee-validate + zod, vue-i18n</li>
            </ul>
          </div>
          <div class="space-y-2">
            <h3 class="text-xl font-semibold">
              {{ t('about.technical.backend.title') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>FastAPI (Python, async)</li>
              <li>PostgreSQL + SQLAlchemy async</li>
              <li>JWT auth, Redis, modular routers</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="ai-context" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('aiContext.title') }}
        </h2>
        <p class="text-muted-foreground">
          {{ t('aiContext.subtitle') }}
        </p>

        <Card>
          <CardHeader>
            <div class="flex items-center justify-between gap-4">
              <div>
                <CardTitle>
                  {{ t('aiContext.card.title') }}
                </CardTitle>
                <CardDescription>
                  {{ t('aiContext.card.description') }}
                </CardDescription>
              </div>
              <Button @click="handleCopy">
                <Copy v-if="!copied" class="size-4" />
                <Check v-else class="size-4" />
                {{ copied ? t('common.copyToClipboard.copied') : t('common.copyToClipboard.copy') }}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre class="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded-md border overflow-x-auto max-h-[600px] overflow-y-auto">{{ aiContextMarkdown }}</pre>
          </CardContent>
        </Card>
      </section>
    </div>
  </AuthenticatedLayout>
</template>
