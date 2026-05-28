<script setup lang="ts">
defineProps<{
  title?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click="emit('close')">
    <div 
      class="bg-mono-500 rounded-[25px] w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      @click.stop
    >
      <div v-if="title" class="px-6 py-4 border-b border-mono-600 flex justify-between items-center bg-mono-700">
        <h3 class="text-2xl font-bold text-white">{{ title }}</h3>
        <button @click="emit('close')" class="text-mono-200 hover:text-white transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="p-6 overflow-y-auto">
        <slot></slot>
      </div>
      
      <div v-if="$slots.footer" class="p-6 border-t border-mono-600 bg-mono-700/50">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>
