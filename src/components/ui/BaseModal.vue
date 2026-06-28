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
      class="bg-mono-900 border border-mono-700 rounded-xl w-full max-w-lg shadow-[0_10px_40px_-10px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh]"
      @click.stop
    >
      <div v-if="title" class="px-6 py-4 border-b border-mono-800 flex justify-between items-center bg-mono-950">
        <h3 class="text-xl font-bold font-mono text-mono-50 tracking-wide [text-shadow:0_0_8px_rgba(255,255,255,0.2)]">{{ title }}</h3>
        <button @click="emit('close')" class="text-mono-400 hover:text-white hover:bg-mono-800 p-1 rounded-md transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="p-6 overflow-y-auto">
        <slot></slot>
      </div>
      
      <div v-if="$slots.footer" class="p-6 border-t border-mono-800 bg-mono-950/50">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>
