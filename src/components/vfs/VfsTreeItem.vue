<script setup lang="ts">
import { computed } from 'vue';
import { useVfsStore } from '@/stores/vfs';
import type { Folder } from '@/types/vfs';
import { File as FileIcon } from 'lucide-vue-next';

interface Props {
  folder: Folder;
  depth: number;
}

const props = defineProps<Props>();

const vfsStore = useVfsStore();

// 判斷當前資料夾是否展開
const isExpanded = computed(() => vfsStore.expandedFolders[props.folder.id] || false);

// 判斷是否為當前瀏覽的資料夾
const isCurrent = computed(() => vfsStore.currentFolder?.id === props.folder.id);

// 獲取快取中的子項目
const cachedContent = computed(() => vfsStore.directoryCache[props.folder.id]);

// 點擊資料夾名稱時：載入該資料夾
const handleFolderClick = async (e: Event) => {
  e.stopPropagation();
  await vfsStore.fetchDirectory(props.folder.id);
};

// 點擊展開符號時：切換展開狀態
const handleToggleExpand = (e: Event) => {
  e.stopPropagation();
  vfsStore.toggleFolderExpand(props.folder.id);
};
</script>

<template>
  <div class="flex flex-col select-none">
    <!-- 資料夾節點列 -->
    <div 
      class="flex items-center py-2 px-2 hover:bg-mono-800/50 cursor-pointer text-sm font-mono text-mono-300 hover:text-mono-50 group transition-all rounded-md"
      :style="{ paddingLeft: `${depth * 20 + 8}px` }"
      @click="handleFolderClick"
    >
      <!-- 展開/折疊按鈕 -->
      <span 
        class="w-5 h-5 flex items-center justify-center mr-2 text-mono-500 group-hover:text-mono-300 transition-transform duration-150 active:scale-95 shrink-0"
        @click.stop="handleToggleExpand"
      >
        <span :class="['transform transition-transform inline-block font-bold', isExpanded ? 'rotate-90 text-mono-200' : '']">
          &gt;
        </span>
      </span>

      <!-- 資料夾名稱 -->
      <span :class="['truncate flex-grow', isCurrent ? 'text-mono-50 font-bold [text-shadow:0_0_8px_rgba(255,255,255,0.4)]' : '']">
        {{ folder.name }}
      </span>
    </div>

    <!-- 子目錄與子檔案遞迴展示 -->
    <div v-if="isExpanded && cachedContent" class="flex flex-col relative before:content-[''] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[1px] before:bg-mono-800 before:ml-[18px]">
      <!-- 渲染子資料夾 -->
      <VfsTreeItem 
        v-for="subf in cachedContent.folders" 
        :key="subf.id"
        :folder="subf" 
        :depth="depth + 1" 
      />

      <!-- 渲染子檔案 (唯讀展示) -->
      <div 
        v-for="file in cachedContent.files" 
        :key="file.id"
        class="flex items-center py-2 px-2 text-sm font-mono text-mono-500 select-none group transition-all rounded-md"
        :style="{ paddingLeft: `${(depth + 1) * 20 + 8}px` }"
      >
        <span class="w-5 h-5 flex items-center justify-center mr-2 text-mono-600 shrink-0">
          <FileIcon class="w-3.5 h-3.5" />
        </span>
        <span class="truncate">{{ file.name }}</span>
      </div>
    </div>
  </div>
</template>
