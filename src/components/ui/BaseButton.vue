<script setup lang="ts">
import { computed } from 'vue';
import type { BaseButtonProps } from '@/types/ui';

const props = withDefaults(defineProps<BaseButtonProps>(), {
  variant: 'primary',
  disabled: false,
  loading: false,
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>();

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'primary':
      return 'bg-mono-50 text-mono-950 hover:bg-white shadow-[0_0_15px_rgba(255,255,255,0.2)] active:scale-95 border border-transparent';
    case 'secondary':
      return 'bg-mono-800 text-mono-50 hover:bg-mono-700 active:scale-95 border border-mono-600 shadow-sm';
    case 'ghost':
      return 'bg-transparent text-mono-200 hover:text-white hover:bg-mono-800 border border-transparent active:scale-95';
    case 'white':
      return 'bg-white text-black hover:bg-mono-100 active:scale-95 shadow-[0_0_15px_rgba(255,255,255,0.2)] border border-transparent';
    case 'outline':
      return 'bg-transparent border border-mono-500 text-mono-50 hover:bg-mono-800 active:scale-95 shadow-sm';
    default:
      return 'bg-mono-50 text-mono-950 hover:bg-white shadow-[0_0_15px_rgba(255,255,255,0.2)] active:scale-95 border border-transparent';
  }
});
</script>

<template>
  <button
    :disabled="disabled || loading"
    @click="emit('click', $event)"
    :class="[
      'flex items-center justify-center px-6 py-2.5 rounded-md font-mono font-bold text-sm transition-all duration-200',
      variantClasses,
      (disabled || loading) ? 'opacity-50 cursor-not-allowed scale-100' : 'cursor-pointer'
    ]"
  >
    <svg v-if="loading" class="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    <slot></slot>
  </button>
</template>
