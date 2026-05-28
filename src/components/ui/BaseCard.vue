<template>
  <div class="bg-mono-300 rounded-[25px] flex flex-col items-center w-full max-w-[490px] shadow-lg relative overflow-hidden">
    <div v-if="$slots.header" class="bg-black w-full flex items-center justify-center py-4 px-8">
      <slot name="header"></slot>
    </div>
    <div class="w-full flex flex-col gap-4 p-6 sm:p-10">
      <slot></slot>
    </div>
  </div>
</template>
