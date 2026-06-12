import { defineStore } from 'pinia';
import { ref, reactive, watch } from 'vue';
import { vfsApi } from '@/api/vfs';
import type { Folder, FileItem, Breadcrumb, UploadTask } from '@/types/vfs';
import axios from 'axios';

export const useVfsStore = defineStore('vfs', () => {
  const currentFolder = ref<Folder | null>(null);
  const breadcrumbs = ref<Breadcrumb[]>([]);
  const subfolders = ref<Folder[]>([]);
  const files = ref<FileItem[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const uploadTasks = ref<UploadTask[]>([]);

  let errorTimeout: ReturnType<typeof setTimeout> | null = null;
  watch(error, (newVal) => {
    if (errorTimeout) {
      clearTimeout(errorTimeout);
      errorTimeout = null;
    }
    if (newVal) {
      errorTimeout = setTimeout(() => {
        error.value = null;
      }, 5000); // 5秒後自動清除錯誤提示
    }
  });

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
    uploadTasks.value = [];
    // 清空快取
    for (const key in directoryCache) {
      delete directoryCache[key];
    }
    for (const key in expandedFolders) {
      delete expandedFolders[key];
    }
  }

  /**
   * 下載檔案，使用帶有 Token 的請求獲取 Blob，並在瀏覽器本地觸發下載
   */
  async function downloadFileAction(fileId: string, filename: string) {
    try {
      const response = await vfsApi.downloadFile(fileId);
      const contentType = response.headers['content-type'];
      const blob = new Blob([response.data], { type: typeof contentType === 'string' ? contentType : undefined });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      console.error('Failed to download file:', e);
      error.value = '下載檔案失敗';
    }
  }

  /**
   * 更新單個上傳任務的進度百分比
   */
  function updateTaskProgress(task: UploadTask, totalChunks: number, currentChunkIndex?: number, currentChunkProgress: number = 0) {
    const uploadedCount = task.uploadedChunks.length;
    let totalProgress = (uploadedCount / totalChunks);
    
    // 如果傳入當前正在上傳的分塊進度，加權進去
    if (currentChunkIndex !== undefined && !task.uploadedChunks.includes(currentChunkIndex)) {
      totalProgress += (currentChunkProgress / totalChunks);
    }
    
    task.progress = Math.min(Math.round(totalProgress * 100), 99); // 結算前最多到 99%
  }

  /**
   * 執行分塊上傳核心邏輯，支援工業級斷點續傳
   */
  async function executeUploadTask(task: UploadTask) {
    const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB
    const totalChunks = Math.ceil(task.file.size / CHUNK_SIZE) || 1;
    let uploadId = '';

    try {
      // 1. 檢查 LocalStorage 是否有此 taskId 的上傳會話映射
      const cacheKey = `vfs_upload_id_${task.id}`;
      const cachedUploadId = localStorage.getItem(cacheKey);

      if (cachedUploadId) {
        task.status = 'checking';
        try {
          const statusRes = await vfsApi.getUploadStatus(cachedUploadId);
          uploadId = statusRes.data.upload_id;
          task.uploadedChunks = statusRes.data.uploaded_chunks || [];
          task.uploadId = uploadId;
        } catch (statusErr) {
          // 若獲取失敗，代表會話已失效或被過期 GC 刪除
          localStorage.removeItem(cacheKey);
        }
      }

      // 2. 若沒有有效的 cachedUploadId，則初始化一個
      if (!uploadId) {
        const folderId = currentFolder.value?.id || null;
        const initRes = await vfsApi.initUpload(task.filename, totalChunks, folderId);
        uploadId = initRes.data.upload_id;
        task.uploadId = uploadId;
        task.uploadedChunks = [];
        localStorage.setItem(cacheKey, uploadId);
      }

      task.status = 'uploading';

      // 3. 建立取消來源
      const source = axios.CancelToken.source();
      task.cancelSource = source;

      // 4. 開始上傳分塊
      for (let i = 0; i < totalChunks; i++) {
        // 檢查是否已被取消
        if ((task.status as string) === 'canceled') return;

        // 若該分塊已上傳，更新進度後跳過
        if (task.uploadedChunks.includes(i)) {
          updateTaskProgress(task, totalChunks);
          continue;
        }

        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, task.file.size);
        const chunkBlob = task.file.slice(start, end);

        // 每塊上傳
        let chunkProgress = 0;
        let retries = 3;
        let success = false;
        
        while (retries > 0 && !success) {
          try {
            await vfsApi.uploadChunk(
              uploadId,
              i,
              chunkBlob,
              (progressEvent) => {
                if (progressEvent.total) {
                  chunkProgress = progressEvent.loaded / progressEvent.total;
                  updateTaskProgress(task, totalChunks, i, chunkProgress);
                }
              },
              source.token
            );
            success = true;
          } catch (err: any) {
            if (axios.isCancel(err)) {
              throw err; // 若為使用者主動取消，直接拋出不重試
            }
            retries--;
            if (retries === 0) {
              throw err; // 重試用盡，宣告失敗
            }
            // 稍等 1 秒後重試
            await new Promise(r => setTimeout(r, 1000));
          }
        }

        // 上傳成功後加入已上傳列表
        task.uploadedChunks.push(i);
        updateTaskProgress(task, totalChunks);
      }

      // 5. 結算合併
      if (task.status === 'uploading') {
        task.status = 'finalizing'; // 合併中的狀態
        await vfsApi.finalizeUpload(uploadId);
        task.status = 'success';
        task.progress = 100;
        localStorage.removeItem(cacheKey);
        
        // 重新載入當前目錄
        await fetchDirectory(currentFolder.value?.id);

        // 成功後延遲 3 秒自動移除任務
        setTimeout(() => {
          removeTask(task.id);
        }, 3000);
      }
    } catch (e: any) {
      if (axios.isCancel(e)) {
        task.status = 'canceled';
      } else {
        console.error(`Failed to upload task ${task.id}:`, e);
        task.status = 'failed';
        error.value = e.response?.data?.detail || '檔案上傳失敗';
      }
    }
  }

  /**
   * 新增上傳任務
   */
  function addUploadTaskAction(file: File) {
    const taskId = `${file.name}-${file.size}-${file.lastModified}`;
    
    // 避免重複加入相同的進行中任務
    const existing = uploadTasks.value.find(t => t.id === taskId);
    if (existing && (existing.status === 'uploading' || existing.status === 'checking' || existing.status === 'finalizing')) {
      return;
    }

    const newTask: UploadTask = reactive({
      id: taskId,
      filename: file.name,
      file,
      progress: 0,
      status: 'checking',
      uploadedChunks: [],
    });

    // 如果之前有失敗或取消的，先移除再加，或是直接取代
    const index = uploadTasks.value.findIndex(t => t.id === taskId);
    if (index !== -1) {
      uploadTasks.value[index] = newTask;
    } else {
      uploadTasks.value.push(newTask);
    }

    executeUploadTask(newTask);
  }

  /**
   * 取消上傳任務
   */
  async function cancelUploadAction(taskId: string) {
    const task = uploadTasks.value.find(t => t.id === taskId);
    if (!task) return;

    // 1. 中斷請求
    if (task.cancelSource) {
      task.cancelSource.cancel('User canceled the upload');
    }

    task.status = 'canceled';

    // 2. 呼叫後端 cancel
    if (task.uploadId) {
      try {
        await vfsApi.cancelUpload(task.uploadId);
      } catch (e) {
        console.error('Failed to call cancelUpload API:', e);
      }
    }

    // 3. 清理快取
    const cacheKey = `vfs_upload_id_${task.id}`;
    localStorage.removeItem(cacheKey);
  }

  /**
   * 移除特定任務
   */
  function removeTask(taskId: string) {
    const index = uploadTasks.value.findIndex(t => t.id === taskId);
    if (index !== -1) {
      uploadTasks.value.splice(index, 1);
    }
  }

  /**
   * 清除所有已結束 (非進行中) 的任務
   */
  function clearFinishedTasksAction() {
    uploadTasks.value = uploadTasks.value.filter(
      t => t.status === 'uploading' || t.status === 'checking' || t.status === 'finalizing'
    );
  }

  return {
    currentFolder,
    breadcrumbs,
    subfolders,
    files,
    isLoading,
    error,
    uploadTasks,
    directoryCache,
    expandedFolders,
    fetchDirectory,
    toggleFolderExpand,
    createFolder,
    renameNode,
    moveNode,
    deleteNode,
    clearState,
    downloadFileAction,
    addUploadTaskAction,
    cancelUploadAction,
    clearFinishedTasksAction,
  };
});
