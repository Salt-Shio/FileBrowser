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
      return 'bg-mono-950 text-white font-bold hover:bg-mono-800';
    case 'secondary':
      return 'bg-mono-700 text-white font-medium hover:bg-mono-600';
    case 'ghost':
      return 'bg-transparent text-white font-bold opacity-70 hover:opacity-100 hover:bg-white/10';
    case 'white':
      return 'bg-white text-black font-bold hover:bg-mono-100';
    case 'outline':
      return 'bg-transparent border-2 border-mono-950 text-mono-950 font-bold hover:bg-mono-100';
    default:
      return 'bg-mono-950 text-white font-bold hover:bg-mono-800';
  }
});
</script>

<template>
  <button
    :disabled="disabled || loading"
    @click="emit('click', $event)"
    :class="[
      'flex items-center justify-center px-6 py-3 rounded-[20px] transition-all duration-200',
      variantClasses,
      (disabled || loading) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
    ]"
  >
    <svg v-if="loading" class="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    <slot></slot>
  </button>
</template>
