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
   * 下載檔案，先獲取臨時 Ticket，再建立隱藏的 iframe 觸發下載 (記憶體零開銷，防失敗跳轉)
   */
  async function downloadFileAction(fileId: string, filename: string) {
    try {
      // 1. 獲取臨時下載憑證
      const ticketRes = await vfsApi.getDownloadTicket(fileId);
      const ticket = ticketRes.data.ticket;

      // 2. 建立或獲取隱藏的 iframe 觸發原生下載
      let iframe = document.getElementById('vfs-download-iframe') as HTMLIFrameElement;
      if (!iframe) {
        iframe = document.createElement('iframe');
        iframe.id = 'vfs-download-iframe';
        iframe.style.display = 'none';
        document.body.appendChild(iframe);
      }

      // 監聽 iframe onload 以捕捉下載失敗時的回應內容
      iframe.onload = () => {
        try {
          const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
          if (iframeDoc && iframeDoc.body) {
            const textContent = (iframeDoc.body.textContent || iframeDoc.body.innerText || '').trim();
            if (textContent) {
              const errData = JSON.parse(textContent);
              if (errData && errData.detail) {
                error.value = `下載失敗: ${errData.detail}`;
              }
            }
          }
        } catch (_) {
          // 若為成功下載或解析失敗則靜默忽略
        }
      };

      iframe.src = `/api/vfs/download/${fileId}?ticket=${ticket}`;
    } catch (e: any) {
      console.error('Failed to download file:', e);
      error.value = e.response?.data?.detail || '下載檔案失敗';
      throw e;
    }
  }

  /**
   * 更新單個上傳任務的進度百分比 (支援多個活躍分塊)
   */
  function updateTaskProgress(task: UploadTask, totalChunks: number, activeProgressMap: Record<number, number> = {}) {
    const uploadedCount = task.uploadedChunks.length;
    let totalProgress = (uploadedCount / totalChunks);

    // 加上活躍中的分塊進度
    let activeProgressSum = 0;
    for (const chunkIndex in activeProgressMap) {
      if (!task.uploadedChunks.includes(Number(chunkIndex))) {
        activeProgressSum += activeProgressMap[chunkIndex];
      }
    }
    totalProgress += (activeProgressSum / totalChunks);

    task.progress = Math.min(Math.round(totalProgress * 100), 99); // 結算前最多到 99%
  }

  /**
   * 執行分塊上傳核心邏輯，支援工業級斷點續傳
   */
  /**
   * 執行分塊上傳核心邏輯，支援工業級斷點續傳
   */
  async function executeUploadTask(task: UploadTask) {
    if (!task.file) {
      error.value = `任務 ${task.filename} 缺少實體檔案，無法執行上傳`;
      task.status = 'failed';
      return;
    }

    let CHUNK_SIZE = Number(import.meta.env.VITE_CHUNK_SIZE_SMALL) || 2 * 1024 * 1024; // 預設 2MB
    if (task.totalSize >= 1024 * 1024 * 1024) {
      CHUNK_SIZE = Number(import.meta.env.VITE_CHUNK_SIZE_LARGE) || 10 * 1024 * 1024;
    } else if (task.totalSize >= 100 * 1024 * 1024) {
      CHUNK_SIZE = Number(import.meta.env.VITE_CHUNK_SIZE_MEDIUM) || 5 * 1024 * 1024;
    }

    const totalChunks = Math.ceil(task.totalSize / CHUNK_SIZE) || 1;
    task.totalChunks = totalChunks;
    let uploadId = '';

    try {
      // 1. 檢查 LocalStorage 是否有此 taskId 的上傳會話映射 (或者任務本身已帶有 uploadId)
      const cacheKey = `vfs_upload_id_${task.id}`;
      const cachedUploadId = task.uploadId || localStorage.getItem(cacheKey);

      if (cachedUploadId) {
        task.status = 'checking';
        try {
          const folderId = currentFolder.value?.id || task.targetFolderId || null;
          const statusRes = await vfsApi.resumeUpload(cachedUploadId, task.lastModified, folderId);
          
          // 【防呆機制】：若環境變數的 Chunk Size 變更，導致前端算出的 totalChunks 與後端舊會話不符，直接捨棄舊會話重新上傳
          if (statusRes.data.total_chunks !== totalChunks) {
            throw new Error('分塊設定已變更，放棄舊會話');
          }

          uploadId = statusRes.data.upload_id;
          task.uploadedChunks = statusRes.data.uploaded_chunks || [];
          task.uploadId = uploadId;
          task.uploadToken = statusRes.data.upload_token;
        } catch (statusErr) {
          // 若獲取失敗，代表會話已失效、防呆驗證不通過，或目標目錄衝突，清除快取重新開始
          localStorage.removeItem(cacheKey);
          task.uploadId = undefined;
        }
      }

      if (!uploadId) {
        const folderId = currentFolder.value?.id || null;
        const initRes = await vfsApi.initUpload(task.filename, task.totalSize, CHUNK_SIZE, task.lastModified, folderId);
        uploadId = initRes.data.upload_id;
        task.uploadId = uploadId;
        task.uploadToken = initRes.data.upload_token;
        task.uploadedChunks = initRes.data.uploaded_chunks || [];
        localStorage.setItem(cacheKey, uploadId);
      }

      task.status = 'uploading';

      // 3. 建立取消來源
      const source = axios.CancelToken.source();
      task.cancelSource = source;

      // 4. 開始上傳分塊 (併發 Promise Pool)
      const CONCURRENCY = Number(import.meta.env.VITE_UPLOAD_CONCURRENCY) || 3;
      const pendingChunks: number[] = [];
      for (let i = 0; i < totalChunks; i++) {
        if (!task.uploadedChunks.includes(i)) {
          pendingChunks.push(i);
        } else {
          // 初始化時也順便更新一下進度
          updateTaskProgress(task, totalChunks, {});
        }
      }

      const activeProgressMap: Record<number, number> = {};
      let hasError = false; // 發生錯誤時標記，以中斷其他 Worker

      const worker = async () => {
        while (pendingChunks.length > 0 && !hasError) {
          if ((task.status as string) === 'paused' || (task.status as string) === 'canceled') return;

          const i = pendingChunks.shift()!;
          const start = i * CHUNK_SIZE;
          const end = Math.min(start + CHUNK_SIZE, task.totalSize);
          const chunkBlob = task.file!.slice(start, end);

          let retries = 3;
          let success = false;
          
          while (retries > 0 && !success && !hasError) {
            if ((task.status as string) === 'paused' || (task.status as string) === 'canceled') return;
            try {
              await vfsApi.uploadChunk(
                uploadId,
                i,
                task.uploadToken!,
                chunkBlob,
                (progressEvent) => {
                  if (progressEvent.total) {
                    activeProgressMap[i] = progressEvent.loaded / progressEvent.total;
                    updateTaskProgress(task, totalChunks, activeProgressMap);
                  }
                },
                source.token
              );
              success = true;
              delete activeProgressMap[i]; // 完成後移除活躍進度
              task.uploadedChunks.push(i);
              updateTaskProgress(task, totalChunks, activeProgressMap);
            } catch (err: any) {
              if (axios.isCancel(err) || err.response?.status === 401) {
                hasError = true;
                throw err; // 取消或被劫持，不重試直接終止所有 Worker
              }
              retries--;
              if (retries === 0) {
                hasError = true;
                throw err;
              }
              await new Promise(r => setTimeout(r, 1000));
            }
          }
        }
      };

      const workers = [];
      for (let w = 0; w < CONCURRENCY; w++) {
        workers.push(worker());
      }
      await Promise.all(workers);

      // 5. 結算合併
      if (task.status === 'uploading') {
        task.status = 'finalizing'; // 合併中的狀態
        await vfsApi.finalizeUpload(uploadId, task.uploadToken!);
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
        task.status = 'paused';
      } else {
        console.error(`Failed to upload task ${task.id}:`, e);
        task.status = 'failed';
        error.value = e.response?.data?.detail || '檔案上傳失敗';
      }
    }
  }

  /**
   * 初始化並載入所有伺服器端活躍任務 (正向補齊與反向 GC 清理)
   */
  async function fetchActiveTasksAction() {
    try {
      const res = await vfsApi.getActiveSessions();
      const sessions = res.data.sessions || [];
      const sessionMap = new Map<string, any>(sessions.map((s: any) => [s.upload_id, s]));

      // 1. 反向清理 (幽靈任務防呆)：若本地任務是 waiting 或 paused，但伺服器說它不存在了，代表被伺服器 GC 刪除，移除本地任務
      for (let i = uploadTasks.value.length - 1; i >= 0; i--) {
        const t = uploadTasks.value[i];
        if (t.status === 'waiting_for_file' || t.status === 'paused') {
          if (t.uploadId && !sessionMap.has(t.uploadId)) {
            uploadTasks.value.splice(i, 1);
          }
        }
      }

      // 2. 正向補齊：走訪伺服器任務，若本地沒有這個任務，就把它加進來當作 waiting_for_file
      for (const s of sessions) {
        const exists = uploadTasks.value.find(t => t.uploadId === s.upload_id);
        if (!exists) {
          uploadTasks.value.push({
            id: s.upload_id, // 直接拿 upload_id 當前端 ID
            uploadId: s.upload_id,
            filename: s.filename,
            targetFolderId: s.target_folder_id,
            totalSize: s.total_size,
            totalChunks: s.total_chunks,
            lastModified: s.last_modified,
            progress: s.total_chunks > 0 ? Math.round((s.uploaded_chunks_count / s.total_chunks) * 100) : 0,
            status: 'waiting_for_file',
            uploadedChunks: [], // 尚未取得詳細陣列，先放空
          });
        }
      }
    } catch (e) {
      console.error('Failed to fetch active sessions:', e);
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
      totalSize: file.size,
      totalChunks: 0,
      lastModified: file.lastModified,
      progress: 0,
      status: 'checking',
      uploadedChunks: [],
    });

    const index = uploadTasks.value.findIndex(t => t.id === taskId);
    if (index !== -1) {
      uploadTasks.value[index] = newTask;
    } else {
      uploadTasks.value.push(newTask);
    }

    executeUploadTask(newTask);
  }

  /**
   * 暫停上傳任務 (僅中斷前端發送請求，保留後端紀錄)
   */
  function pauseUploadAction(taskId: string) {
    const task = uploadTasks.value.find(t => t.id === taskId);
    if (!task) return;

    if (task.cancelSource) {
      task.cancelSource.cancel('User paused the upload');
    } else {
      task.status = 'paused';
    }
  }

  /**
   * 恢復上傳任務 (支援 F5 重新整理後選檔恢復)
   */
  function resumeUploadTaskAction(taskId: string, file?: File) {
    const task = uploadTasks.value.find(t => t.id === taskId);
    if (!task) return;

    if (task.status === 'waiting_for_file') {
      if (!file) {
        error.value = "必須選擇檔案才能恢復上傳";
        return;
      }
      // 嚴格校驗檔案特徵
      if (file.name !== task.filename || file.lastModified !== task.lastModified || file.size !== task.totalSize) {
        error.value = `檔案特徵不符：請選擇正確的 ${task.filename} 檔案`;
        return;
      }
      task.file = file;
      task.status = 'checking';
      executeUploadTask(task);
    } else if (task.status === 'paused' || task.status === 'failed') {
      if (!task.file) {
        task.status = 'waiting_for_file'; // 記憶體沒檔案了，要求補檔
        return;
      }
      task.status = 'checking';
      executeUploadTask(task);
    }
  }

  /**
   * 取消上傳任務 (中斷請求並通知後端刪除)
   */
  async function cancelUploadAction(taskId: string) {
    const task = uploadTasks.value.find(t => t.id === taskId);
    if (!task) return;

    // 1. 中斷請求
    if (task.cancelSource) {
      task.cancelSource.cancel('User canceled the upload');
    }

    task.status = 'canceled' as any;

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
    removeTask(task.id);
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
   * 清除所有已結束 (非進行中/非暫停/非等待) 的任務
   */
  function clearFinishedTasksAction() {
    uploadTasks.value = uploadTasks.value.filter(
      t => ['uploading', 'checking', 'finalizing', 'paused', 'waiting_for_file'].includes(t.status)
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
    fetchActiveTasksAction,
    addUploadTaskAction,
    pauseUploadAction,
    resumeUploadTaskAction,
    cancelUploadAction,
    clearFinishedTasksAction,
  };
});
