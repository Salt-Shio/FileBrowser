import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器：自動帶上 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const vfsApi = {
  /**
   * 獲取指定資料夾內容，包含子資料夾、檔案與麵包屑。
   * @param folderId 可選資料夾 UUID，為空時獲取 Root
   */
  listDirectory(folderId?: string) {
    return api.get('/vfs/ls', {
      params: folderId ? { folder_id: folderId } : {},
    });
  },
  /**
   * 建立新的虛擬資料夾
   */
  createFolder(name: string, parentId?: string | null) {
    return api.post('/vfs/mkdir', {
      name,
      parent_id: parentId || null,
    });
  },
  /**
   * 重新命名資料夾或檔案
   */
  renameNode(nodeId: string, nodeType: 'folder' | 'file', newName: string) {
    return api.post('/vfs/rename', {
      node_id: nodeId,
      node_type: nodeType,
      new_name: newName,
    });
  },
  /**
   * 搬移資料夾或檔案到指定目錄
   */
  moveNode(nodeId: string, nodeType: 'folder' | 'file', targetParentId: string | null) {
    return api.post('/vfs/move', {
      node_id: nodeId,
      node_type: nodeType,
      target_parent_id: targetParentId,
    });
  },
  /**
   * 邏輯刪除資料夾或檔案
   */
  deleteNode(nodeId: string, nodeType: 'folder' | 'file') {
    return api.post('/vfs/delete', {
      node_id: nodeId,
      node_type: nodeType,
    });
  },
  /**
   * 獲取臨時下載憑證
   */
  getDownloadTicket(fileId: string) {
    return api.post(`/vfs/download/ticket/${fileId}`);
  },
  /**
   * 下載指定檔案 (使用臨時憑證)
   */
  downloadFile(fileId: string, ticket: string) {
    return api.get(`/vfs/download/${fileId}`, {
      params: { ticket },
      responseType: 'blob',
    });
  },
  /**
   * 初始化分塊上傳
   */
  initUpload(filename: string, totalSize: number, chunkSize: number, lastModified: number, targetFolderId?: string | null) {
    return api.post('/vfs/upload/init', {
      filename,
      total_size: totalSize,
      chunk_size: chunkSize,
      last_modified: lastModified,
      target_folder_id: targetFolderId || null,
    });
  },
  /**
   * 上傳單個分塊
   */
  uploadChunk(
    uploadId: string,
    chunkIndex: number,
    uploadToken: string,
    fileChunk: Blob,
    onUploadProgress?: (progressEvent: any) => void,
    cancelToken?: any
  ) {
    const formData = new FormData();
    formData.append('upload_id', uploadId);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('upload_token', uploadToken);
    formData.append('file', fileChunk, 'chunk');
    return api.post('/vfs/upload/chunk', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
      cancelToken,
    });
  },
  /**
   * 發起跨資料夾斷點續傳
   */
  resumeUpload(uploadId: string, lastModified: number, targetFolderId?: string | null) {
    return api.post('/vfs/upload/resume', {
      upload_id: uploadId,
      last_modified: lastModified,
      target_folder_id: targetFolderId || null,
    });
  },
  /**
   * 取消分塊上傳
   */
  cancelUpload(uploadId: string) {
    return api.post('/vfs/upload/cancel', {
      upload_id: uploadId,
    });
  },
  /**
   * 結算完成上傳
   */
  finalizeUpload(uploadId: string, uploadToken: string) {
    return api.post('/vfs/upload/finalize', {
      upload_id: uploadId,
      upload_token: uploadToken,
    });
  },
  /**
   * 獲取伺服器端活躍的上傳會話
   */
  getActiveSessions() {
    return api.get('/vfs/upload/sessions');
  },
};
