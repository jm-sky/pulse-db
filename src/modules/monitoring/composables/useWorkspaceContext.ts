import { computed, ref } from 'vue'
import { MOCK_INSTANCES, type MockInstance } from '@/modules/monitoring/mocks/instances'

const selectedInstanceId = ref<string>(MOCK_INSTANCES[0]?.id ?? '')
const timeRangeLabel = ref('Last 1 hour')

export function useWorkspaceContext() {
  const selectedInstance = computed<MockInstance | undefined>(() =>
    MOCK_INSTANCES.find(i => i.id === selectedInstanceId.value),
  )

  function selectInstance(id: string) {
    selectedInstanceId.value = id
  }

  return {
    instances: MOCK_INSTANCES,
    selectedInstanceId,
    selectedInstance,
    timeRangeLabel,
    selectInstance,
  }
}
