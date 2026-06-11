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
};
