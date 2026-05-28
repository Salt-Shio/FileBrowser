<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BaseInputProps } from '@/types/ui';
import { Eye, EyeOff } from '@lucide/vue';

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
      return 'bg-mono-700 border-3 border-black rounded-[20px]';
    default:
      return 'bg-mono-700 border-3 border-black rounded-[20px]';
  }
});
</script>

<template>
  <div class="flex flex-col gap-2 w-full">
    <label v-if="label" class="text-xl font-medium text-black px-2">{{ label }}</label>
    
    <div :class="['flex items-center overflow-hidden w-full relative h-[54px]', containerClasses]">
      <input
        :type="inputType"
        :value="modelValue"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        :placeholder="placeholder"
        :disabled="disabled"
        class="w-full h-full bg-transparent text-white placeholder-mono-400 text-lg py-2 px-4 outline-none disabled:opacity-50"
      />
      
      <button 
        v-if="type === 'password'" 
        type="button"
        @click="togglePassword"
        class="flex items-center justify-center bg-[#434141] h-full w-[54px] absolute right-0 top-0 border-l-3 border-black hover:bg-mono-600 transition-colors"
      >
        <Eye v-if="showPassword" class="w-6 h-6 text-white" />
        <EyeOff v-else class="w-6 h-6 text-white" />
      </button>
    </div>
  </div>
</template>
