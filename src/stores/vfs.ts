import { defineStore } from 'pinia';
import { ref, reactive } from 'vue';
import { vfsApi } from '@/api/vfs';
import type { Folder, FileItem, Breadcrumb } from '@/types/vfs';

export const useVfsStore = defineStore('vfs', () => {
  const currentFolder = ref<Folder | null>(null);
  const breadcrumbs = ref<Breadcrumb[]>([]);
  const subfolders = ref<Folder[]>([]);
  const files = ref<FileItem[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // 用於左側樹狀目錄的快取結構：key 為 folderId, value 為該目錄下的子項
  const directoryCache = reactive<Record<string, { folders: Folder[]; files: FileItem[] }>>({});
  
  // 記錄哪些資料夾目前在左側目錄樹是展開的
  const expandedFolders = reactive<Record<string, boolean>>({});

  /**
   * 載入指定目錄內容，並更新當前瀏覽狀態與目錄樹快取。
   * @param folderId 可選資料夾 UUID
   */
  async function fetchDirectory(folderId?: string) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await vfsApi.listDirectory(folderId);
      const data = response.data;
      
      currentFolder.value = data.current_folder;
      breadcrumbs.value = data.breadcrumbs;
      subfolders.value = data.subfolders;
      files.value = data.files;

      const targetId = data.current_folder.id;

      // 1. 將讀取的子項快取起來，供左側目錄樹使用
      directoryCache[targetId] = {
        folders: data.subfolders,
        files: data.files,
      };

      // 2. 自動將當前目錄以及所有父級麵包屑目錄設為展開
      expandedFolders[targetId] = true;
      data.breadcrumbs.forEach((bc: Breadcrumb) => {
        expandedFolders[bc.id] = true;
      });
    } catch (e: any) {
      console.error('Failed to fetch VFS directory:', e);
      error.value = e.response?.data?.detail || '加載檔案系統失敗';
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 切換資料夾在左側目錄樹的展開/折疊狀態
   */
  function toggleFolderExpand(folderId: string) {
    expandedFolders[folderId] = !expandedFolders[folderId];
    
    // 如果展開且快取中還沒有資料，就順便載入一下
    if (expandedFolders[folderId] && !directoryCache[folderId]) {
      fetchDirectory(folderId);
    }
  }

  /**
   * 建立新的資料夾
   */
  async function createFolder(name: string, parentId?: string | null) {
    isLoading.value = true;
    error.value = null;
    try {
      const pid = parentId || currentFolder.value?.id || null;
      await vfsApi.createFolder(name, pid);
      
      // 清除父目錄的目錄樹快取，確保重新拉取最新目錄樹
      if (pid) {
        delete directoryCache[pid];
      }
      
      // 重新載入當前目錄
      await fetchDirectory(currentFolder.value?.id);
    } catch (e: any) {
      console.error('Failed to create folder:', e);
      error.value = e.response?.data?.detail || '建立資料夾失敗';
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 重新命名資料夾或檔案
   */
  async function renameNode(nodeId: string, nodeType: 'folder' | 'file', newName: string) {
    isLoading.value = true;
    error.value = null;
    try {
      await vfsApi.renameNode(nodeId, nodeType, newName);
      
      // 清除當前目錄快取以刷新樹狀選單的顯示名稱
      if (currentFolder.value) {
        delete directoryCache[currentFolder.value.id];
      }
      
      await fetchDirectory(currentFolder.value?.id);
    } catch (e: any) {
      console.error('Failed to rename node:', e);
      error.value = e.response?.data?.detail || '重新命名失敗';
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 搬移資料夾或檔案
   */
  async function moveNode(nodeId: string, nodeType: 'folder' | 'file', targetParentId: string | null) {
    isLoading.value = true;
    error.value = null;
    try {
      await vfsApi.moveNode(nodeId, nodeType, targetParentId);
      
      // 清除來源目錄快取與目標目錄快取
      if (currentFolder.value) {
        delete directoryCache[currentFolder.value.id];
      }
      if (targetParentId) {
        delete directoryCache[targetParentId];
      }
      
      await fetchDirectory(currentFolder.value?.id);
    } catch (e: any) {
      console.error('Failed to move node:', e);
      error.value = e.response?.data?.detail || '搬移失敗';
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 邏輯刪除資料夾或檔案
   */
  async function deleteNode(nodeId: string, nodeType: 'folder' | 'file') {
    isLoading.value = true;
    error.value = null;
    try {
      await vfsApi.deleteNode(nodeId, nodeType);
      
      // 清除當前目錄快取
      if (currentFolder.value) {
        delete directoryCache[currentFolder.value.id];
      }
      
      await fetchDirectory(currentFolder.value?.id);
    } catch (e: any) {
      console.error('Failed to delete node:', e);
      error.value = e.response?.data?.detail || '刪除失敗';
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  function clearState() {
    currentFolder.value = null;
    breadcrumbs.value = [];
    subfolders.value = [];
    files.value = [];
    error.value = null;
    // 清空快取
    for (const key in directoryCache) {
      delete directoryCache[key];
    }
    for (const key in expandedFolders) {
      delete expandedFolders[key];
    }
  }

  return {
    currentFolder,
    breadcrumbs,
    subfolders,
    files,
    isLoading,
    error,
    directoryCache,
    expandedFolders,
    fetchDirectory,
    toggleFolderExpand,
    createFolder,
    renameNode,
    moveNode,
    deleteNode,
    clearState,
  };
});
