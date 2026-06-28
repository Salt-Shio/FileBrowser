<script setup lang="ts">
import { onMounted, computed, ref } from 'vue';
import { useVfsStore } from '@/stores/vfs';
import { vfsApi } from '@/api/vfs';
import VfsTreeItem from '@/components/vfs/VfsTreeItem.vue';
import BaseModal from '@/components/ui/BaseModal.vue';
import BaseInput from '@/components/ui/BaseInput.vue';
import BaseButton from '@/components/ui/BaseButton.vue';
import type { Folder } from '@/types/vfs';
import { 
  Pencil, 
  FolderInput, 
  Trash2, 
  Plus,
  Folder as FolderIcon,
  File as FileIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  Loader2,
  X
} from 'lucide-vue-next';

const vfsStore = useVfsStore();

// Modal 狀態控制
const showMkdirModal = ref(false);
const showRenameModal = ref(false);
const showDeleteModal = ref(false);
const showMoveModal = ref(false);

// 被選取的操作節點資訊
const selectedNodeId = ref('');
const selectedNodeType = ref<'folder' | 'file'>('folder');
const selectedNodeName = ref('');

// 表單輸入變數
const newFolderName = ref('');
const renameValue = ref('');

// 迷你 VFS 瀏覽器狀態 (用於移動節點彈窗)
const miniCurrentFolderId = ref('');
const miniBreadcrumbs = ref<any[]>([]);
const miniSubfolders = ref<Folder[]>([]);
const miniLoading = ref(false);

// 頁面載入時自動拉取 VFS 根目錄內容與活躍上傳任務
onMounted(async () => {
  await Promise.all([
    vfsStore.fetchDirectory(),
    vfsStore.fetchActiveTasksAction()
  ]);
});

// 計算 Root 資料夾作為左側目錄樹的起點
const rootFolder = computed<Folder | null>(() => {
  if (vfsStore.breadcrumbs.length > 0) {
    return {
      id: vfsStore.breadcrumbs[0].id,
      name: vfsStore.breadcrumbs[0].name,
      parent_id: null,
      owner_id: vfsStore.breadcrumbs[0].id,
      created_at: '',
      updated_at: '',
    } as Folder;
  }
  if (vfsStore.currentFolder && vfsStore.currentFolder.parent_id === null) {
    return vfsStore.currentFolder;
  }
  return null;
});

// 格式化當前右側標題顯示的路徑：如 "root > Folder1"
const pathDisplay = computed(() => {
  if (vfsStore.breadcrumbs.length === 0) {
    return vfsStore.currentFolder?.name || 'Root';
  }
  return vfsStore.breadcrumbs.map(b => b.name).join(' > ');
});

// 迷你 VFS 路徑顯示
const miniPathDisplay = computed(() => {
  if (miniBreadcrumbs.value.length === 0) {
    return 'Root';
  }
  return miniBreadcrumbs.value.map(b => b.name).join(' > ');
});

// 日期格式化 helper (對齊 Figma: 2026/5/21 10:50)
const formatDate = (dateStr: string) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1);
  const dd = String(d.getDate());
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${yyyy}/${mm}/${dd} ${hh}:${min}`;
};

// 處理點擊麵包屑回溯
const handleBreadcrumbClick = async (folderId: string) => {
  await vfsStore.fetchDirectory(folderId);
};

// 點擊右側列表的子資料夾
const handleFolderClick = async (folderId: string) => {
  await vfsStore.fetchDirectory(folderId);
};

// --- 異動操作按鈕點擊事件 ---

// 1. 新增資料夾
const openMkdirModal = () => {
  newFolderName.value = '';
  showMkdirModal.value = true;
};

const handleConfirmMkdir = async () => {
  if (!newFolderName.value.trim()) return;
  try {
    await vfsStore.createFolder(newFolderName.value.trim());
    showMkdirModal.value = false;
  } catch (e) {
    // 錯誤由 store 处理並顯示在 error 狀態中
  }
};

// 2. 重新命名
const openRenameModal = (nodeId: string, nodeType: 'folder' | 'file', currentName: string) => {
  selectedNodeId.value = nodeId;
  selectedNodeType.value = nodeType;
  selectedNodeName.value = currentName;
  renameValue.value = currentName;
  showRenameModal.value = true;
};

const handleConfirmRename = async () => {
  if (!renameValue.value.trim() || renameValue.value.trim() === selectedNodeName.value) return;
  try {
    await vfsStore.renameNode(selectedNodeId.value, selectedNodeType.value, renameValue.value.trim());
    showRenameModal.value = false;
  } catch (e) {
    // 錯誤由 store 处理
  }
};

// 3. 邏輯刪除
const openDeleteModal = (nodeId: string, nodeType: 'folder' | 'file', nodeName: string) => {
  selectedNodeId.value = nodeId;
  selectedNodeType.value = nodeType;
  selectedNodeName.value = nodeName;
  showDeleteModal.value = true;
};

const handleConfirmDelete = async () => {
  try {
    await vfsStore.deleteNode(selectedNodeId.value, selectedNodeType.value);
    showDeleteModal.value = false;
  } catch (e) {
    // 錯誤由 store 处理
  }
};

// 4. 移動節點與迷你 VFS 瀏覽器邏輯
const openMoveModal = async (nodeId: string, nodeType: 'folder' | 'file', nodeName: string) => {
  selectedNodeId.value = nodeId;
  selectedNodeType.value = nodeType;
  selectedNodeName.value = nodeName;
  
  // 初始化為根目錄
  const rootId = vfsStore.breadcrumbs[0]?.id || vfsStore.currentFolder?.id || '';
  await loadMiniDirectory(rootId);
  showMoveModal.value = true;
};

const loadMiniDirectory = async (folderId: string) => {
  miniLoading.value = true;
  try {
    const response = await vfsApi.listDirectory(folderId);
    miniBreadcrumbs.value = response.data.breadcrumbs;
    // 前置防護：排除被移動的資料夾自己，防止移入自身或循環引用
    miniSubfolders.value = response.data.subfolders.filter((f: Folder) => f.id !== selectedNodeId.value);
    miniCurrentFolderId.value = response.data.current_folder.id;
  } catch (e) {
    console.error('Failed to load mini directory:', e);
  } finally {
    miniLoading.value = false;
  }
};

const handleMiniFolderClick = async (folderId: string) => {
  await loadMiniDirectory(folderId);
};

const handleConfirmMove = async () => {
  // 防護：不能移入當前所在的父目錄（無效移動）
  const currentParentId = selectedNodeType.value === 'folder' 
    ? (vfsStore.subfolders.find(f => f.id === selectedNodeId.value)?.parent_id)
    : (vfsStore.files.find(f => f.id === selectedNodeId.value)?.folder_id);

  if (miniCurrentFolderId.value === currentParentId) {
    alert('此物件已在該目錄中！');
    return;
  }

  try {
    await vfsStore.moveNode(selectedNodeId.value, selectedNodeType.value, miniCurrentFolderId.value);
    showMoveModal.value = false;
  } catch (e) {
    // 錯誤由 store 处理
  }
};

// --- 檔案上傳與下載邏輯 ---

const fileInput = ref<HTMLInputElement | null>(null);

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files) return;
  for (let i = 0; i < target.files.length; i++) {
    vfsStore.addUploadTaskAction(target.files[i]);
  }
  target.value = ''; // 允許重複上傳相同檔案觸發 change
};

const downloadingFiles = ref<Record<string, boolean>>({});

const handleDownloadFile = async (fileId: string, filename: string) => {
  if (downloadingFiles.value[fileId]) return;
  downloadingFiles.value[fileId] = true;
  try {
    await vfsStore.downloadFileAction(fileId, filename);
  } catch (err) {
    console.error('Failed to trigger download:', err);
  } finally {
    // 3 秒後自動解除按鈕禁用與轉圈狀態，防重複狂點
    setTimeout(() => {
      downloadingFiles.value[fileId] = false;
    }, 3000);
  }
};

const pauseUpload = (taskId: string) => {
  vfsStore.pauseUploadAction(taskId);
};

const resumeUpload = (taskId: string) => {
  vfsStore.resumeUploadTaskAction(taskId);
};

const resumeFileInput = ref<HTMLInputElement | null>(null);
const currentResumeTaskId = ref('');

const triggerResumeFileInput = (taskId: string) => {
  currentResumeTaskId.value = taskId;
  resumeFileInput.value?.click();
};

const handleResumeFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files || target.files.length === 0) return;
  const file = target.files[0];
  vfsStore.resumeUploadTaskAction(currentResumeTaskId.value, file);
  target.value = '';
};

const cancelUpload = async (taskId: string) => {
  await vfsStore.cancelUploadAction(taskId);
};

const activeUploadCount = computed(() => {
  return vfsStore.uploadTasks.filter(t => t.status === 'uploading' || t.status === 'checking').length;
});

const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'waiting_for_file': return '等待補檔';
    case 'checking': return '探測中';
    case 'uploading': return '上傳中';
    case 'finalizing': return '合併中...';
    case 'success': return '成功';
    case 'failed': return '失敗';
    case 'paused': return '已暫停';
    case 'canceled': return '已取消';
    default: return status;
  }
};
</script>

<template>
  <div class="min-h-full w-full relative flex flex-col items-center pt-8">
    <!-- 頁面最大寬度容器 -->
    <div class="w-full max-w-[1440px] px-10 flex flex-col h-full gap-8">
      
      <!-- 全局錯誤公告 -->
      <div v-if="vfsStore.error" class="w-full bg-red-950/80 border border-red-500 rounded-lg p-4 flex items-center justify-center shadow-[0_0_20px_rgba(239,68,68,0.2)] backdrop-blur-md relative shrink-0">
        <span class="text-red-100 font-mono text-sm font-bold flex items-center gap-2">
          <span class="text-red-500">[ERROR]</span> {{ vfsStore.error }}
        </span>
        <button @click="vfsStore.error = null" class="absolute right-4 p-1.5 hover:bg-red-900 rounded-md transition-colors cursor-pointer text-red-300 hover:text-white">
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- 主要分欄瀏覽區域 -->
      <div class="flex flex-col md:flex-row gap-8 w-full h-[70vh]">
        
        <!-- 左欄：樹狀目錄導航 -->
        <div class="bg-mono-950/50 md:w-[320px] shrink-0 flex flex-col overflow-y-auto border border-mono-700 rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.5)] relative">
          <div class="p-4 border-b border-mono-800 bg-mono-900/80 backdrop-blur-md sticky top-0 z-10 shadow-sm">
            <h2 class="font-mono text-mono-400 text-sm tracking-widest uppercase">Directory Tree</h2>
          </div>
          <div class="flex flex-col gap-2 p-4">
            <!-- 載入中狀態 -->
            <div v-if="vfsStore.isLoading && !rootFolder" class="text-mono-400 text-sm font-mono animate-pulse">
              &gt; Loading directory structure...
            </div>
            
            <!-- 遞迴目錄樹起點 -->
            <VfsTreeItem 
              v-else-if="rootFolder" 
              :folder="rootFolder" 
              :depth="0"
            />
            
            <div v-else class="text-mono-500 text-sm italic">
              No directory data
            </div>
          </div>
        </div>

        <!-- 右欄：詳細列表操作區 -->
        <div class="flex-grow flex flex-col h-full bg-mono-950/50 relative overflow-hidden rounded-xl border border-mono-700 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
          
          <!-- 當前目錄標題與操作欄 -->
          <div class="bg-mono-900/80 backdrop-blur-md h-[70px] px-6 flex items-center justify-between shrink-0 border-b border-mono-700 gap-4 sticky top-0 z-10 shadow-sm">
            <p class="font-mono font-medium text-xl text-mono-50 truncate flex-grow [text-shadow:0_0_8px_rgba(255,255,255,0.2)]">
              {{ pathDisplay }}
            </p>
            
            <!-- 操作按鈕組 -->
            <div class="flex items-center gap-3 shrink-0">
              <button 
                @click="openMkdirModal"
                class="bg-mono-800 text-mono-50 hover:bg-mono-700 hover:text-white border border-mono-600 rounded-md px-4 py-2 text-sm font-bold flex items-center gap-2 cursor-pointer transition-all shadow-sm active:scale-95"
              >
                <Plus class="w-4 h-4" />
                新建資料夾
              </button>

              <button 
                @click="triggerFileInput"
                class="bg-mono-50 text-mono-900 hover:bg-white border border-transparent rounded-md px-4 py-2 text-sm font-bold flex items-center gap-2 cursor-pointer transition-all shadow-[0_0_10px_rgba(255,255,255,0.2)] active:scale-95"
              >
                <UploadIcon class="w-4 h-4" />
                上傳檔案
              </button>
              <input 
                type="file" 
                ref="fileInput" 
                class="hidden" 
                multiple 
                @change="handleFileChange" 
              />
              <input 
                type="file" 
                ref="resumeFileInput" 
                class="hidden" 
                @change="handleResumeFileChange" 
              />
            </div>
          </div>

          <!-- 主要列表區域 -->
          <div class="flex-grow overflow-y-auto relative bg-transparent">
            <!-- 載入狀態遮罩 -->
            <div 
              v-if="vfsStore.isLoading" 
              class="absolute inset-0 bg-mono-950/40 backdrop-blur-sm flex items-center justify-center z-10"
            >
              <div class="bg-mono-900 text-mono-50 px-6 py-3 border border-mono-700 rounded-lg font-mono text-sm shadow-2xl animate-pulse flex items-center gap-2">
                <Loader2 class="w-4 h-4 animate-spin" />
                Loading...
              </div>
            </div>


            <!-- 檔案與資料夾列表 -->
            <div class="flex flex-col w-full text-sm">
              <!-- 0. 返回上一層 (..) -->
              <div 
                v-if="vfsStore.currentFolder && vfsStore.currentFolder.parent_id !== null"
                class="h-[60px] px-6 flex items-center justify-between border-b border-mono-800/50 hover:bg-mono-800/50 cursor-pointer text-mono-200 hover:text-white font-medium select-none group transition-all"
                @click="handleFolderClick(vfsStore.currentFolder.parent_id)"
              >
                <span class="truncate pr-4 flex items-center gap-3 font-mono">
                  <span class="text-mono-500">&gt;</span>
                  <span>..</span>
                </span>
                <span class="shrink-0 text-mono-500 text-right"></span>
              </div>

              <!-- 1. 子資料夾清單 -->
              <div 
                v-for="folder in vfsStore.subfolders" 
                :key="folder.id"
                class="h-[60px] px-6 flex items-center justify-between border-b border-mono-800/50 hover:bg-mono-800/50 cursor-pointer text-mono-200 hover:text-white font-medium select-none group transition-all"
                @click="handleFolderClick(folder.id)"
              >
                <span class="truncate pr-4 flex items-center gap-3">
                  <FolderIcon class="w-5 h-5 text-mono-400 group-hover:text-mono-50 transition-colors" />
                  <span>{{ folder.name }}</span>
                </span>
                
                <span class="shrink-0 text-mono-500 text-xs font-mono group-hover:hidden block">
                  {{ formatDate(folder.updated_at) }}
                </span>

                <div class="hidden group-hover:flex items-center gap-2" @click.stop>
                  <button @click="openRenameModal(folder.id, 'folder', folder.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><Pencil class="w-4 h-4" /></button>
                  <button @click="openMoveModal(folder.id, 'folder', folder.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><FolderInput class="w-4 h-4" /></button>
                  <button @click="openDeleteModal(folder.id, 'folder', folder.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><Trash2 class="w-4 h-4" /></button>
                </div>
              </div>

              <!-- 2. 子檔案清單 -->
              <div 
                v-for="file in vfsStore.files" 
                :key="file.id"
                class="h-[60px] px-6 flex items-center justify-between border-b border-mono-800/50 hover:bg-mono-800/50 text-mono-200 hover:text-white font-medium select-none group transition-all"
              >
                <span class="truncate pr-4 flex items-center gap-3">
                  <FileIcon class="w-5 h-5 text-mono-500 group-hover:text-mono-50 transition-colors" />
                  <span>{{ file.name }}</span>
                </span>

                <span class="shrink-0 text-mono-500 text-xs font-mono group-hover:hidden block">
                  {{ formatDate(file.updated_at) }}
                </span>

                <div class="hidden group-hover:flex items-center gap-2" @click.stop>
                  <button 
                    @click="handleDownloadFile(file.id, file.name)"
                    :disabled="downloadingFiles[file.id]"
                    class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Loader2 v-if="downloadingFiles[file.id]" class="w-4 h-4 animate-spin" />
                    <DownloadIcon v-else class="w-4 h-4" />
                  </button>
                  <button @click="openRenameModal(file.id, 'file', file.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><Pencil class="w-4 h-4" /></button>
                  <button @click="openMoveModal(file.id, 'file', file.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><FolderInput class="w-4 h-4" /></button>
                  <button @click="openDeleteModal(file.id, 'file', file.name)" class="p-1.5 hover:bg-mono-700 rounded-md text-mono-400 hover:text-white transition-colors cursor-pointer"><Trash2 class="w-4 h-4" /></button>
                </div>
              </div>

              <!-- 3. 空目錄提示 -->
              <div 
                v-if="!vfsStore.isLoading && vfsStore.subfolders.length === 0 && vfsStore.files.length === 0" 
                class="py-20 text-center text-mono-500 text-sm font-mono italic"
              >
                // empty directory
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ==================== MODALS ==================== -->
    <BaseModal v-if="showMkdirModal" title="新建資料夾" @close="showMkdirModal = false">
      <div class="flex flex-col gap-4 text-mono-50">
        <div v-if="vfsStore.error" class="bg-mono-800 border border-mono-600 text-mono-200 p-3 rounded-md text-sm text-center font-mono">
          {{ vfsStore.error }}
        </div>
        <BaseInput v-model="newFolderName" label="資料夾名稱" placeholder="請輸入名稱" @keyup.enter="handleConfirmMkdir" />
        <div class="flex gap-3 mt-4">
          <BaseButton variant="ghost" class="flex-1 text-sm py-2 border border-mono-700 hover:bg-mono-800" @click="showMkdirModal = false">取消</BaseButton>
          <BaseButton class="flex-1 text-sm py-2 bg-mono-50 text-black hover:bg-mono-200" @click="handleConfirmMkdir">建立</BaseButton>
        </div>
      </div>
    </BaseModal>

    <BaseModal v-if="showRenameModal" title="重新命名" @close="showRenameModal = false">
      <div class="flex flex-col gap-4 text-mono-50">
        <div v-if="vfsStore.error" class="bg-mono-800 border border-mono-600 text-mono-200 p-3 rounded-md text-sm text-center font-mono">
          {{ vfsStore.error }}
        </div>
        <BaseInput v-model="renameValue" label="新名稱" placeholder="請輸入新名稱" @keyup.enter="handleConfirmRename" />
        <div class="flex gap-3 mt-4">
          <BaseButton variant="ghost" class="flex-1 text-sm py-2 border border-mono-700 hover:bg-mono-800" @click="showRenameModal = false">取消</BaseButton>
          <BaseButton class="flex-1 text-sm py-2 bg-mono-50 text-black hover:bg-mono-200" @click="handleConfirmRename">確認修改</BaseButton>
        </div>
      </div>
    </BaseModal>

    <BaseModal v-if="showDeleteModal" title="確認刪除" @close="showDeleteModal = false">
      <div class="flex flex-col gap-4 text-mono-50">
        <div v-if="vfsStore.error" class="bg-mono-800 border border-mono-600 text-mono-200 p-3 rounded-md text-sm text-center font-mono">
          {{ vfsStore.error }}
        </div>
        <div class="text-center py-4">
          <p class="text-lg font-bold text-white mb-2">確定要刪除此項目嗎？</p>
          <p class="text-mono-400 text-sm">
            您即將刪除「<span class="font-mono text-mono-50">{{ selectedNodeName }}</span>」。
          </p>
        </div>
        <div class="flex gap-3">
          <BaseButton variant="ghost" class="flex-1 text-sm py-2 border border-mono-700 hover:bg-mono-800" @click="showDeleteModal = false">取消</BaseButton>
          <BaseButton variant="primary" class="flex-1 bg-mono-200 text-black hover:bg-white text-sm py-2" @click="handleConfirmDelete">確定刪除</BaseButton>
        </div>
      </div>
    </BaseModal>

    <BaseModal v-if="showMoveModal" title="移動至指定資料夾" @close="showMoveModal = false">
      <div class="flex flex-col gap-4 text-mono-50">
        <div v-if="vfsStore.error" class="bg-mono-800 border border-mono-600 text-mono-200 p-3 rounded-md text-sm text-center font-mono">
          {{ vfsStore.error }}
        </div>
        <div class="bg-mono-900 p-3 rounded-md border border-mono-700 text-mono-300 text-sm font-mono truncate shadow-inner">
          Destination: <span class="text-mono-50">{{ miniPathDisplay }}</span>
        </div>
        <div class="bg-mono-950 border border-mono-700 rounded-md h-[240px] overflow-y-auto relative flex flex-col shadow-inner">
          <div v-if="miniLoading" class="absolute inset-0 bg-mono-950/50 flex items-center justify-center z-10 backdrop-blur-sm">
            <span class="bg-mono-800 border border-mono-600 px-3 py-1.5 rounded-md text-sm font-mono animate-pulse shadow-lg">Loading...</span>
          </div>
          <div v-if="miniBreadcrumbs.length > 1" class="h-[45px] px-4 flex items-center border-b border-mono-800 hover:bg-mono-800 cursor-pointer text-sm font-mono text-mono-400 hover:text-white transition-colors" @click="handleMiniFolderClick(miniBreadcrumbs[miniBreadcrumbs.length - 2].id)">
            <span>&gt; ..</span>
          </div>
          <div v-if="miniSubfolders.length > 0" class="flex flex-col">
            <div v-for="subf in miniSubfolders" :key="subf.id" class="h-[45px] px-4 flex items-center border-b border-mono-800 hover:bg-mono-800 cursor-pointer text-sm gap-2 text-mono-200 hover:text-white transition-colors" @click="handleMiniFolderClick(subf.id)">
              <FolderIcon class="w-4 h-4 text-mono-500" />
              <span>{{ subf.name }}</span>
            </div>
          </div>
          <div v-else-if="!miniLoading" class="p-8 text-center text-mono-600 italic text-xs font-mono">
            // no subdirectories
          </div>
        </div>
        <div class="flex gap-3 mt-2">
          <BaseButton variant="ghost" class="flex-1 text-sm py-2 border border-mono-700 hover:bg-mono-800" @click="showMoveModal = false">取消</BaseButton>
          <BaseButton class="flex-1 text-sm py-2 bg-mono-50 text-black hover:bg-mono-200" @click="handleConfirmMove">移至此處</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- 5. 懸浮上傳進度面板 -->
    <div 
      v-if="vfsStore.uploadTasks.length > 0"
      class="fixed bottom-6 right-6 z-50 w-[360px] bg-mono-950 border border-mono-700 rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col text-mono-50 backdrop-blur-xl"
    >
      <div class="bg-mono-900/80 text-mono-50 px-4 py-3 flex items-center justify-between border-b border-mono-700">
        <div class="flex items-center gap-2">
          <span class="text-sm font-bold font-sans">傳輸管理</span>
          <span class="text-[10px] font-mono bg-mono-800 border border-mono-600 px-1.5 py-0.5 rounded text-mono-300">
            {{ activeUploadCount }} / {{ vfsStore.uploadTasks.length }}
          </span>
        </div>
        <button 
          @click="vfsStore.clearFinishedTasksAction()"
          class="text-[10px] font-mono bg-mono-800 text-mono-200 hover:bg-mono-700 hover:text-white px-2 py-1 rounded transition-colors cursor-pointer border border-mono-600"
        >
          CLEAR
        </button>
      </div>

      <div class="max-h-[300px] overflow-y-auto p-3 flex flex-col gap-2 bg-mono-950/50">
        <div 
          v-for="task in vfsStore.uploadTasks" 
          :key="task.id"
          class="bg-mono-900 border border-mono-700 rounded-lg p-3 flex flex-col gap-2 relative shadow-sm"
        >
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium truncate max-w-[180px]" :title="task.filename">
              {{ task.filename }}
            </span>
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-mono-800 text-mono-300 border border-mono-700">
              {{ getStatusLabel(task.status) }}
            </span>
          </div>

          <!-- 進度條 (白/灰科技感) -->
          <div class="w-full bg-mono-950 border border-mono-700 rounded-full h-3 overflow-hidden relative">
            <div 
              class="bg-mono-50 h-full transition-all duration-300"
              :style="{ width: `${task.progress}%` }"
            ></div>
            <span class="absolute inset-0 flex items-center justify-center text-[8px] font-mono font-bold mix-blend-difference text-white">
              {{ task.progress }}%
            </span>
          </div>

          <div class="flex items-center justify-between text-[10px] mt-1 font-mono">
            <span class="text-mono-500">
              {{ formatBytes(task.totalSize) }}
            </span>
            <div class="flex items-center gap-1.5">
              <template v-if="task.status === 'uploading' || task.status === 'checking'">
                <button @click="pauseUpload(task.id)" class="text-mono-400 hover:text-white cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">PAUSE</button>
              </template>
              <template v-else-if="task.status === 'paused'">
                <button @click="resumeUpload(task.id)" class="text-mono-50 hover:text-white cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">RESUME</button>
                <button @click="cancelUpload(task.id)" class="text-mono-500 hover:text-mono-300 cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">CANCEL</button>
              </template>
              <template v-else-if="task.status === 'waiting_for_file'">
                <button @click="triggerResumeFileInput(task.id)" class="text-mono-400 hover:text-white cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">RETRY</button>
                <button @click="cancelUpload(task.id)" class="text-mono-500 hover:text-mono-300 cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">CANCEL</button>
              </template>
              <template v-else-if="task.status === 'failed'">
                <button @click="resumeUpload(task.id)" class="text-mono-400 hover:text-white cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">RETRY</button>
                <button @click="cancelUpload(task.id)" class="text-mono-500 hover:text-mono-300 cursor-pointer px-1 py-0.5 rounded hover:bg-mono-800 transition-colors">CANCEL</button>
              </template>
              <span v-else-if="task.status === 'finalizing'" class="text-mono-300 animate-pulse">MERGING...</span>
              <span v-else-if="task.status === 'success'" class="text-mono-50">DONE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--color-mono-700);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-mono-500);
}
</style>
