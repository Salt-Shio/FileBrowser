<script setup lang="ts">
import { computed } from 'vue';
import { useVfsStore } from '@/stores/vfs';
import type { Folder } from '@/types/vfs';

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
      class="flex items-center py-1 hover:bg-mono-400/20 cursor-pointer text-2xl font-medium text-black group transition-colors"
      :style="{ paddingLeft: `${depth * 24}px` }"
      @click="handleFolderClick"
    >
      <!-- 展開/折疊按鈕 -->
      <span 
        class="w-6 h-6 flex items-center justify-center mr-1 text-black font-bold transition-transform duration-150 active:scale-95"
        @click.stop="handleToggleExpand"
      >
        <span :class="['transform transition-transform inline-block', isExpanded ? 'rotate-90' : '']">
          &gt;
        </span>
      </span>

      <!-- 資料夾名稱 -->
      <span :class="['truncate', isCurrent ? 'font-bold underline' : '']">
        {{ folder.name }}
      </span>
    </div>

    <!-- 子目錄與子檔案遞迴展示 -->
    <div v-if="isExpanded && cachedContent" class="flex flex-col">
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
        class="flex items-center py-1 text-2xl font-medium text-black/80 select-none"
        :style="{ paddingLeft: `${(depth + 1) * 24 + 24}px` }"
      >
        <span class="truncate">{{ file.name }}</span>
      </div>
    </div>
  </div>
</template>
