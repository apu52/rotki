<script setup lang="ts">
import { type BaseMessage } from '@/types/messages';

withDefaults(
  defineProps<{
    status: BaseMessage | null;
  }>(),
  {
    status: null
  }
);
</script>

<template>
  <div
    v-if="status && (status.success || status.error)"
    class="action-status-indicator"
  >
    <RuiAlert
      class="mb-0"
      dense
      :type="status.success ? 'success' : 'error'"
      text
      outlined
    >
      {{ status.success || status.error }}
    </RuiAlert>
  </div>
</template>

<style scoped lang="scss">
.action-status-indicator {
  height: 48px;
}
</style>
