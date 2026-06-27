export interface Breadcrumb {
  id: string;
  name: string;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface FileItem {
  id: string;
  name: string;
  folder_id: string | null;
  owner_id: string;
  size: number;
  mime_type: string | null;
  hash_sha256: string;
  created_at: string;
  updated_at: string;
}

export interface BrowseResponse {
  current_folder: Folder;
  breadcrumbs: Breadcrumb[];
  subfolders: Folder[];
  files: FileItem[];
}

export interface UploadTask {
  id: string; // 隨機或雜湊的前端臨時 ID (我們可以用 `${filename}-${file.size}-${file.lastModified}`)
  uploadId?: string; // 後端傳回的 upload_id
  uploadToken?: string; // 後端傳回的防護金鑰
  filename: string;
  file?: File;
  targetFolderId?: string | null;
  totalSize: number;
  totalChunks: number;
  lastModified: number;
  progress: number; // 0 - 100
  status: 'waiting_for_file' | 'checking' | 'uploading' | 'finalizing' | 'success' | 'failed' | 'paused';
  uploadedChunks: number[];
  cancelSource?: any; // 用於取消 Axios 請求的 CancelTokenSource
}
