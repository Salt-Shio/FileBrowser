<template>
  <div class="bg-mono-950/50 border border-mono-700 rounded-xl flex flex-col items-center w-full max-w-[490px] shadow-[0_4px_20px_rgba(0,0,0,0.5)] relative overflow-hidden backdrop-blur-sm">
    <div v-if="$slots.header" class="w-full flex items-center justify-center py-5 px-8 border-b border-mono-800 bg-mono-900/30">
      <slot name="header"></slot>
    </div>
    <div class="w-full flex flex-col gap-4 p-6 sm:p-10">
      <slot></slot>
    </div>
  </div>
</template>
