<script setup lang="ts">
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import LoginForm from '@/modules/auth/components/LoginForm.vue'
import { useLoginModal } from '@/shared/composables/useLoginModal'
import type { IAuthService } from '@/modules/auth/types/auth.type'

// Optional authService prop for dependency injection (useful for testing with mocks)
const props = defineProps<{
  authService?: IAuthService
}>()

const { isOpen, close, handleSuccess } = useLoginModal()

// Handle successful login
const onLoginSuccess = () => {
  handleSuccess()
}

// Note: authService is optional. If not provided, LoginForm uses the default
// authService instance from useAuth composable. Pass mockAuthService for testing.
</script>

<template>
  <Dialog :open="isOpen" @update:open="(open) => !open && close()">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Session Expired</DialogTitle>
        <DialogDescription>
          Your session has expired. Please log in again to continue.
        </DialogDescription>
      </DialogHeader>
      <LoginForm :auth-service="props.authService" @success="onLoginSuccess" />
    </DialogContent>
  </Dialog>
</template>

