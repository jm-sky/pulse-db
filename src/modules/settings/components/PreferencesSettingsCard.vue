<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { Settings } from 'lucide-vue-next'
import { useForm } from 'vee-validate'
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import Select from '@/components/ui/select/Select.vue'
import SelectContent from '@/components/ui/select/SelectContent.vue'
import SelectGroup from '@/components/ui/select/SelectGroup.vue'
import SelectItem from '@/components/ui/select/SelectItem.vue'
import SelectLabel from '@/components/ui/select/SelectLabel.vue'
import SelectTrigger from '@/components/ui/select/SelectTrigger.vue'
import SelectValue from '@/components/ui/select/SelectValue.vue'
import Separator from '@/components/ui/separator/Separator.vue'
import { useSettings } from '@/modules/settings/composables/useSettings'
import { settingsSchema } from '@/modules/settings/validation/settings.schema'
import { useDarkMode } from '@/shared/composables/useDarkMode'
import { type SupportedLocale, useLocale } from '@/shared/i18n'
import ImageProcessingModeRadioGroup from './ImageProcessingModeRadioGroup.vue'
import type { ISettingsService, Settings as SettingsType } from '@/modules/settings/types/settings.type'

const props = defineProps<{
  service?: ISettingsService
}>()

const { t } = useI18n()
const { currentLocale } = useLocale()
const { isDark } = useDarkMode()
const { settingsQuery, settings, updateSettings, isLoading, isUpdating, isError } = useSettings(props.service)

const getThemeValue = (darkMode: boolean | undefined) => {
  return darkMode ? 'dark' : 'light'
}

const { handleSubmit, setValues } = useForm({
  validationSchema: toTypedSchema(settingsSchema),
  initialValues: {
    darkMode: getThemeValue(settings.value?.darkMode),
    locale: settings.value?.locale ?? currentLocale.value,
    profilePublic: settings.value?.profilePublic ?? false,
    emailPublic: settings.value?.emailPublic ?? false,
    imageProcessingMode: settings.value?.imageProcessingMode ?? 'balanced',
  }
})

watch(() => settingsQuery.data.value, (val: SettingsType | undefined) => {
  if (val) {
    setValues({
      darkMode: getThemeValue(val.darkMode),
      locale: val.locale,
      profilePublic: val.profilePublic ?? false,
      emailPublic: val.emailPublic ?? false,
      imageProcessingMode: val.imageProcessingMode ?? 'balanced',
    })
  }
})

watch(() => currentLocale.value, (val: SupportedLocale) => {
  setValues({ locale: val })
}, {
  immediate: true,
})

watch(() => isDark.value, (val: boolean) => {
  setValues({ darkMode: getThemeValue(val) })
}, {
  immediate: true,
})


const onSubmit = handleSubmit(async (values) => {
  await updateSettings({
    darkMode: values.darkMode === 'dark',
    locale: values.locale,
    profilePublic: values.profilePublic,
    emailPublic: values.emailPublic,
    imageProcessingMode: values.imageProcessingMode ?? null,
  })
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <Settings :size="20" />
        <CardTitle>{{ t('settings.page.sections.preferences.title') }}</CardTitle>
      </div>
      <CardDescription>{{ t('settings.page.sections.preferences.description') }}</CardDescription>
    </CardHeader>
    <CardContent :class="{ 'opacity-50': isUpdating }">
      <div v-if="isLoading" class="space-y-4">
        <div class="h-16 bg-muted rounded animate-pulse" />
        <div class="h-16 bg-muted rounded animate-pulse" />
      </div>

      <div v-else-if="isError" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4">
        {{ t('settings.page.error_prefix') }}
      </div>

      <form v-else class="space-y-6" @submit="onSubmit">
        <div class="grid gap-6 md:grid-cols-2">
          <!-- Theme -->
          <div class="space-y-3">
            <FormField v-slot="{ componentField }" name="darkMode">
              <FormItem>
                <FormLabel required>
                  {{ t('settings.page.sections.theme.label') }}
                </FormLabel>
                <p class="text-sm text-muted-foreground">
                  {{ t('settings.page.sections.theme.subtitle') }}
                </p>
                <FormControl>
                  <Select v-bind="componentField">
                    <SelectTrigger>
                      <SelectValue :placeholder="t('settings.page.sections.theme.placeholder')" class="min-w-20" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectLabel>{{ t('settings.page.sections.theme.group_label') }}</SelectLabel>
                        <SelectItem value="light">
                          {{ t('settings.page.sections.theme.options.light') }}
                        </SelectItem>
                        <SelectItem value="dark">
                          {{ t('settings.page.sections.theme.options.dark') }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>
          </div>

          <!-- Locale -->
          <div class="space-y-3">
            <FormField v-slot="{ componentField }" name="locale">
              <FormItem>
                <FormLabel required>
                  {{ t('settings.page.sections.locale.label') }}
                </FormLabel>
                <p class="text-sm text-muted-foreground">
                  {{ t('settings.page.sections.locale.subtitle') }}
                </p>
                <FormControl>
                  <Select v-bind="componentField">
                    <SelectTrigger>
                      <SelectValue :placeholder="t('settings.page.sections.locale.placeholder')" class="min-w-20" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectLabel>{{ t('settings.page.sections.locale.group_label') }}</SelectLabel>
                        <SelectItem value="en">
                          {{ t('settings.page.sections.locale.options.en') }}
                        </SelectItem>
                        <SelectItem value="pl">
                          {{ t('settings.page.sections.locale.options.pl') }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>
          </div>
        </div>

        <!-- Profile Public -->
        <FormField v-slot="{ componentField, handleChange }" name="profilePublic">
          <FormItem v-slot="{ id }" class="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
            <Checkbox
              :id="id"
              :model-value="componentField.modelValue"
              @update:model-value="handleChange"
            />
            <div class="flex-1 space-y-1">
              <FormLabel :label="$t('settings.page.sections.profilePublic.label')" class="cursor-pointer" />
              <p class="text-sm text-muted-foreground">
                {{ $t('settings.page.sections.profilePublic.subtitle') }}
              </p>
            </div>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Email Public -->
        <FormField v-slot="{ componentField, handleChange }" name="emailPublic">
          <FormItem v-slot="{ id }" class="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
            <Checkbox
              :id="id"
              :model-value="componentField.modelValue"
              @update:model-value="handleChange"
            />
            <div class="flex-1 space-y-1">
              <FormLabel :label="$t('settings.page.sections.emailPublic.label')" class="cursor-pointer" />
              <p class="text-sm text-muted-foreground">
                {{ $t('settings.page.sections.emailPublic.subtitle') }}
              </p>
            </div>
            <FormMessage />
          </FormItem>
        </FormField>

        <Separator />

        <!-- Image Processing Mode -->
        <div class="space-y-3">
          <FormField v-slot="{ componentField }" name="imageProcessingMode">
            <FormItem>
              <FormLabel required>
                {{ t('settings.preferences.imageProcessingMode.label') }}
              </FormLabel>
              <p class="text-sm text-muted-foreground">
                {{ t('settings.preferences.imageProcessingMode.subtitle') }}
              </p>
              <FormControl>
                <ImageProcessingModeRadioGroup v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
        </div>

        <div class="flex justify-end">
          <Button type="submit" :loading="isUpdating">
            {{ t('settings.page.save') }}
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>

