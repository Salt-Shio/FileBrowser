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
