<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BaseInputProps } from '@/types/ui';
import { Eye, EyeOff } from 'lucide-vue-next';

const props = withDefaults(defineProps<BaseInputProps>(), {
  type: 'text',
  disabled: false,
  variant: 'default',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>();

// Password Visibility Controller Logic
const showPassword = ref(false);
const inputType = computed(() => {
  if (props.type === 'password') {
    return showPassword.value ? 'text' : 'password';
  }
  return props.type;
});

const togglePassword = () => {
  showPassword.value = !showPassword.value;
};

// Variant logic
const containerClasses = computed(() => {
  switch (props.variant) {
    case 'default':
      return 'bg-mono-950 border border-mono-700 rounded-lg shadow-inner focus-within:border-mono-500 focus-within:shadow-[0_0_8px_rgba(255,255,255,0.1)] transition-all';
    default:
      return 'bg-mono-950 border border-mono-700 rounded-lg shadow-inner focus-within:border-mono-500 focus-within:shadow-[0_0_8px_rgba(255,255,255,0.1)] transition-all';
  }
});
</script>

<template>
  <div class="flex flex-col gap-2 w-full">
    <label v-if="label" class="text-sm font-mono font-medium text-mono-300 px-1">{{ label }}</label>
    
    <div :class="['flex items-center overflow-hidden w-full relative h-[45px]', containerClasses]">
      <input
        :type="inputType"
        :value="modelValue"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        :placeholder="placeholder"
        :disabled="disabled"
        class="w-full h-full bg-transparent text-mono-50 placeholder-mono-600 text-sm py-2 px-3 outline-none disabled:opacity-50 font-mono"
      />
      
      <button 
        v-if="type === 'password'" 
        type="button"
        @click="togglePassword"
        class="flex items-center justify-center bg-mono-900 h-full w-[45px] absolute right-0 top-0 border-l border-mono-700 hover:bg-mono-800 transition-colors cursor-pointer"
      >
        <Eye v-if="showPassword" class="w-5 h-5 text-mono-400" />
        <EyeOff v-else class="w-5 h-5 text-mono-400" />
      </button>
    </div>
  </div>
</template>
