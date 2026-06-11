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
  Download as DownloadIcon
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

// 頁面載入時自動拉取 VFS 根目錄內容
onMounted(async () => {
  await vfsStore.fetchDirectory();
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

const handleDownloadFile = async (fileId: string, filename: string) => {
  await vfsStore.downloadFileAction(fileId, filename);
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
    case 'checking': return '探測中';
    case 'uploading': return '上傳中';
    case 'finalizing': return '合併中...';
    case 'success': return '成功';
    case 'failed': return '失敗';
    case 'canceled': return '已取消';
    default: return status;
  }
};
</script>

<template>
  <div class="bg-[#707070] min-h-screen w-full relative flex flex-col items-center">
    <!-- 頁面最大寬度容器 (對齊 Figma 1440px 設計) -->
    <div class="w-full max-w-[1440px] px-10 flex flex-col">
      
      <!-- 頂部頁面麵包屑 (基於 Figma Node 17:208) -->
      <div class="py-6 flex items-center justify-start border-b border-mono-800/10">
        <p class="font-['Inter'] font-bold text-3xl text-white underline decoration-solid decoration-auto underline-offset-8">
          主頁 --&gt; 檔案系統
        </p>
      </div>

      <!-- 主要分欄瀏覽區域 (基於 Figma Node 30:174) -->
      <div class="mt-8 flex flex-col md:flex-row gap-6 w-full h-[698px]">
        
        <!-- 左欄：樹狀目錄導航 (基於 Figma Node 29:122) -->
        <div class="bg-transparent md:w-[320px] shrink-0 flex flex-col overflow-y-auto pr-4 border-r border-mono-800/20">
          <div class="flex flex-col gap-2">
            <!-- 載入中狀態 -->
            <div v-if="vfsStore.isLoading && !rootFolder" class="p-4 text-mono-200 text-xl font-medium animate-pulse">
              &gt; 目錄樹載入中...
            </div>
            
            <!-- 遞迴目錄樹起點 -->
            <VfsTreeItem 
              v-else-if="rootFolder" 
              :folder="rootFolder" 
              :depth="0"
            />
            
            <div v-else class="p-4 text-mono-300 text-xl italic">
              無目錄資料
            </div>
          </div>
        </div>

        <!-- 右欄：詳細列表操作區 (基於 Figma Node 29:31) -->
        <div class="flex-grow flex flex-col h-full bg-[#686666] relative overflow-hidden rounded-[25px] border-4 border-black">
          
          <!-- 當前目錄標題與操作欄 (基於 Figma Node 29:30) -->
          <div class="bg-[#494949] h-[77px] px-6 flex items-center justify-between shrink-0 border-b-4 border-black gap-4">
            <p class="font-['Inter'] font-medium text-4xl text-white truncate flex-grow">
              {{ pathDisplay }}
            </p>
            
            <!-- 操作按鈕組 -->
            <div class="flex items-center gap-3 shrink-0">
              <!-- 新增資料夾按鈕 (Brutalist Style) -->
              <button 
                @click="openMkdirModal"
                class="bg-white text-black hover:bg-mono-200 border-3 border-black rounded-[12px] px-4 py-1.5 text-xl font-extrabold flex items-center gap-1.5 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:translate-y-0.5 active:shadow-[0px_0px_0px_0px_rgba(0,0,0,1)] transition-all"
              >
                <Plus class="w-5 h-5 stroke-[3]" />
                新建資料夾
              </button>

              <!-- 上傳檔案按鈕 (Brutalist Style) -->
              <button 
                @click="triggerFileInput"
                class="bg-white text-black hover:bg-mono-200 border-3 border-black rounded-[12px] px-4 py-1.5 text-xl font-extrabold flex items-center gap-1.5 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:translate-y-0.5 active:shadow-[0px_0px_0px_0px_rgba(0,0,0,1)] transition-all"
              >
                <UploadIcon class="w-5 h-5 stroke-[3]" />
                上傳檔案
              </button>
              <input 
                type="file" 
                ref="fileInput" 
                class="hidden" 
                multiple 
                @change="handleFileChange" 
              />
            </div>
          </div>

          <!-- 主要列表區域 (Frame 53 / 29:34) -->
          <div class="flex-grow overflow-y-auto relative bg-[#686666]">
            <!-- 載入狀態遮罩 -->
            <div 
              v-if="vfsStore.isLoading" 
              class="absolute inset-0 bg-black/10 backdrop-blur-[1px] flex items-center justify-center z-10"
            >
              <div class="bg-black text-white px-8 py-4 border-2 border-white rounded-[15px] font-bold text-2xl animate-bounce">
                &gt; 加載中...
              </div>
            </div>

            <!-- 錯誤提示 -->
            <div v-if="vfsStore.error" class="p-6 m-4 bg-red-500/20 border-2 border-red-500 rounded-[15px] text-red-100 text-center text-xl font-bold">
              {{ vfsStore.error }}
            </div>

            <!-- 檔案與資料夾列表 -->
            <div class="flex flex-col w-full">
              <!-- 0. 返回上一層 (..) -->
              <div 
                v-if="vfsStore.currentFolder && vfsStore.currentFolder.parent_id !== null"
                class="h-[77px] px-8 flex items-center justify-between border-b-2 border-black hover:bg-black/10 cursor-pointer text-white font-['Inter'] font-medium text-2xl select-none group transition-all"
                @click="handleFolderClick(vfsStore.currentFolder.parent_id)"
              >
                <!-- 名稱 (資料夾前置 "> ") -->
                <span class="truncate pr-4 flex items-center gap-1">
                  <span>&gt;</span>
                  <span>..</span>
                </span>
                <!-- 修改時間 (空白) -->
                <span class="shrink-0 text-mono-200 text-right"></span>
              </div>

              <!-- 1. 子資料夾清單 -->
              <div 
                v-for="folder in vfsStore.subfolders" 
                :key="folder.id"
                class="h-[77px] px-8 flex items-center justify-between border-b-2 border-black hover:bg-black/10 cursor-pointer text-white font-['Inter'] font-medium text-2xl select-none group transition-all"
                @click="handleFolderClick(folder.id)"
              >
                <!-- 名稱 (資料夾前置 "> ") -->
                <span class="truncate pr-4 flex items-center gap-2">
                  <FolderIcon class="w-6 h-6 text-yellow-400 fill-yellow-400 group-hover:scale-105 transition-transform" />
                  <span>&gt; {{ folder.name }}</span>
                </span>
                
                <!-- 時間戳 (Hover 時隱藏，切換為按鈕) -->
                <span class="shrink-0 text-mono-200 text-right group-hover:hidden block">
                  {{ formatDate(folder.updated_at) }}
                </span>

                <!-- Hover 快捷操作按鈕組 (Hover 時顯示) -->
                <div class="hidden group-hover:flex items-center gap-3" @click.stop>
                  <button 
                    @click="openRenameModal(folder.id, 'folder', folder.name)"
                    title="重新命名"
                    class="p-2 hover:bg-white/20 rounded-lg text-white transition-colors cursor-pointer"
                  >
                    <Pencil class="w-5 h-5" />
                  </button>
                  <button 
                    @click="openMoveModal(folder.id, 'folder', folder.name)"
                    title="移動資料夾"
                    class="p-2 hover:bg-white/20 rounded-lg text-white transition-colors cursor-pointer"
                  >
                    <FolderInput class="w-5 h-5" />
                  </button>
                  <button 
                    @click="openDeleteModal(folder.id, 'folder', folder.name)"
                    title="刪除"
                    class="p-2 hover:bg-red-500/30 rounded-lg text-red-300 hover:text-red-200 transition-colors cursor-pointer"
                  >
                    <Trash2 class="w-5 h-5" />
                  </button>
                </div>
              </div>

              <!-- 2. 子檔案清單 -->
              <div 
                v-for="file in vfsStore.files" 
                :key="file.id"
                class="h-[77px] px-8 flex items-center justify-between border-b-2 border-black hover:bg-black/10 text-white font-['Inter'] font-medium text-2xl select-none group transition-all"
              >
                <!-- 名稱 (檔案不帶 "> ") -->
                <span class="truncate pr-4 flex items-center gap-2">
                  <FileIcon class="w-6 h-6 text-blue-400 fill-blue-400 group-hover:scale-105 transition-transform" />
                  <span>{{ file.name }}</span>
                </span>

                <!-- 時間戳 -->
                <span class="shrink-0 text-mono-200 text-right group-hover:hidden block">
                  {{ formatDate(file.updated_at) }}
                </span>

                <!-- Hover 快捷操作按鈕組 (Hover 時顯示) -->
                <div class="hidden group-hover:flex items-center gap-3" @click.stop>
                  <button 
                    @click="handleDownloadFile(file.id, file.name)"
                    title="下載檔案"
                    class="p-2 hover:bg-white/20 rounded-lg text-white transition-colors cursor-pointer"
                  >
                    <DownloadIcon class="w-5 h-5" />
                  </button>
                  <button 
                    @click="openRenameModal(file.id, 'file', file.name)"
                    title="重新命名"
                    class="p-2 hover:bg-white/20 rounded-lg text-white transition-colors cursor-pointer"
                  >
                    <Pencil class="w-5 h-5" />
                  </button>
                  <button 
                    @click="openMoveModal(file.id, 'file', file.name)"
                    title="移動檔案"
                    class="p-2 hover:bg-white/20 rounded-lg text-white transition-colors cursor-pointer"
                  >
                    <FolderInput class="w-5 h-5" />
                  </button>
                  <button 
                    @click="openDeleteModal(file.id, 'file', file.name)"
                    title="刪除"
                    class="p-2 hover:bg-red-500/30 rounded-lg text-red-300 hover:text-red-200 transition-colors cursor-pointer"
                  >
                    <Trash2 class="w-5 h-5" />
                  </button>
                </div>
              </div>

              <!-- 3. 空目錄提示 -->
              <div 
                v-if="!vfsStore.isLoading && vfsStore.subfolders.length === 0 && vfsStore.files.length === 0" 
                class="p-20 text-center text-mono-300 text-2xl italic"
              >
                此資料夾為空。
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ==================== MODALS ==================== -->

    <!-- 1. 新增資料夾彈窗 -->
    <BaseModal v-if="showMkdirModal" title="新建資料夾" @close="showMkdirModal = false">
      <div class="flex flex-col gap-6 text-black">
        <!-- 錯誤提示 -->
        <div v-if="vfsStore.error" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
          {{ vfsStore.error }}
        </div>
        <BaseInput 
          v-model="newFolderName" 
          label="資料夾名稱" 
          placeholder="請輸入資料夾名稱"
          @keyup.enter="handleConfirmMkdir"
        />
        <div class="flex gap-4 mt-2">
          <BaseButton variant="ghost" class="flex-1 text-xl py-3 border-2 border-black" @click="showMkdirModal = false">
            取消
          </BaseButton>
          <BaseButton class="flex-1 text-xl py-3" @click="handleConfirmMkdir">
            建立
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- 2. 重新命名彈窗 -->
    <BaseModal v-if="showRenameModal" title="重新命名" @close="showRenameModal = false">
      <div class="flex flex-col gap-6 text-black">
        <!-- 錯誤提示 -->
        <div v-if="vfsStore.error" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
          {{ vfsStore.error }}
        </div>
        <BaseInput 
          v-model="renameValue" 
          label="新名稱" 
          placeholder="請輸入新名稱"
          @keyup.enter="handleConfirmRename"
        />
        <div class="flex gap-4 mt-2">
          <BaseButton variant="ghost" class="flex-1 text-xl py-3 border-2 border-black" @click="showRenameModal = false">
            取消
          </BaseButton>
          <BaseButton class="flex-1 text-xl py-3" @click="handleConfirmRename">
            確認修改
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- 3. 刪除確認彈窗 -->
    <BaseModal v-if="showDeleteModal" title="確認刪除" @close="showDeleteModal = false">
      <div class="flex flex-col gap-6 text-black">
        <!-- 錯誤提示 -->
        <div v-if="vfsStore.error" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
          {{ vfsStore.error }}
        </div>
        <div class="text-center p-4">
          <p class="text-2xl font-bold text-white mb-2">確定要刪除此項目嗎？</p>
          <p class="text-mono-200 text-lg">
            您即將刪除「<span class="font-extrabold text-white underline">{{ selectedNodeName }}</span>」。<br>
            此操作會將該節點邏輯移入回收站。
          </p>
        </div>
        <div class="flex gap-4">
          <BaseButton variant="ghost" class="flex-1 text-xl py-3 border-2 border-black" @click="showDeleteModal = false">
            取消
          </BaseButton>
          <BaseButton variant="primary" class="flex-1 bg-red-600 hover:bg-red-500 text-xl py-3 text-white border-2 border-black" @click="handleConfirmDelete">
            確定刪除
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- 4. 移動檔案/目錄彈窗 (迷你 VFS 瀏覽器) -->
    <BaseModal v-if="showMoveModal" title="移動至指定資料夾" @close="showMoveModal = false">
      <div class="flex flex-col gap-4 text-black">
        <!-- 錯誤提示 -->
        <div v-if="vfsStore.error" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
          {{ vfsStore.error }}
        </div>
        
        <!-- 迷你導航路徑 -->
        <div class="bg-mono-700/50 p-3 rounded-xl border-2 border-black text-white text-lg font-bold truncate">
          當前目的地：<span class="text-yellow-400">{{ miniPathDisplay }}</span>
        </div>

        <!-- 迷你 VFS 列表區 -->
        <div class="bg-[#686666] border-3 border-black rounded-2xl h-[280px] overflow-y-auto relative flex flex-col text-white">
          <!-- 載入中狀態 -->
          <div v-if="miniLoading" class="absolute inset-0 bg-black/20 flex items-center justify-center z-10">
            <span class="bg-black border border-white px-4 py-2 rounded-xl text-lg animate-pulse">加載中...</span>
          </div>

          <!-- 上一層按鈕 (當前目的地不是最頂層根目錄時顯示) -->
          <div 
            v-if="miniBreadcrumbs.length > 1"
            class="h-[54px] px-6 flex items-center border-b border-black hover:bg-white/10 cursor-pointer text-lg font-medium gap-1"
            @click="handleMiniFolderClick(miniBreadcrumbs[miniBreadcrumbs.length - 2].id)"
          >
            <span>&gt; ..</span>
          </div>

          <!-- 子資料夾列表 (排除檔案，因為只能移到資料夾裡) -->
          <div v-if="miniSubfolders.length > 0" class="flex flex-col">
            <div 
              v-for="subf in miniSubfolders"
              :key="subf.id"
              class="h-[54px] px-6 flex items-center border-b border-black hover:bg-white/10 cursor-pointer text-lg font-medium gap-2"
              @click="handleMiniFolderClick(subf.id)"
            >
              <FolderIcon class="w-5 h-5 text-yellow-400 fill-yellow-400" />
              <span>&gt; {{ subf.name }}</span>
            </div>
          </div>
          <div v-else-if="!miniLoading" class="p-10 text-center text-mono-300 italic text-base">
            此目錄下無其他子資料夾
          </div>
        </div>

        <!-- 按鈕操作區 -->
        <div class="flex gap-4 mt-2">
          <BaseButton variant="ghost" class="flex-1 text-xl py-3 border-2 border-black" @click="showMoveModal = false">
            取消
          </BaseButton>
          <BaseButton class="flex-1 text-xl py-3" @click="handleConfirmMove">
            移至此處
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- 5. 懸浮上傳進度面板 -->
    <div 
      v-if="vfsStore.uploadTasks.length > 0"
      class="fixed bottom-6 right-6 z-50 w-[380px] bg-[#494949] border-[4px] border-black rounded-[20px] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden flex flex-col text-white"
    >
      <!-- 面板標頭列 -->
      <div class="bg-black text-white px-5 py-3 flex items-center justify-between border-b-3 border-black">
        <span class="text-lg font-extrabold font-['Inter']">上傳傳輸管理</span>
        <span class="text-xs bg-[#707070] border border-white px-2 py-0.5 rounded-full">
          {{ activeUploadCount }} / {{ vfsStore.uploadTasks.length }}
        </span>
      </div>

      <!-- 任務列表 -->
      <div class="max-h-[280px] overflow-y-auto p-4 flex flex-col gap-3 bg-[#686666]">
        <div 
          v-for="task in vfsStore.uploadTasks" 
          :key="task.id"
          class="bg-[#494949] border-2 border-black rounded-xl p-3 flex flex-col gap-2 relative"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold truncate max-w-[220px]" :title="task.filename">
              {{ task.filename }}
            </span>
            <span class="text-xs font-mono font-bold px-1.5 py-0.5 rounded border border-black bg-white text-black">
              {{ getStatusLabel(task.status) }}
            </span>
          </div>

          <!-- 進度條 -->
          <div class="w-full bg-black border-2 border-black rounded-full h-4 overflow-hidden relative">
            <div 
              class="bg-green-400 h-full transition-all duration-300"
              :style="{ width: `${task.progress}%` }"
            ></div>
            <span class="absolute inset-0 flex items-center justify-center text-[10px] font-extrabold text-white mix-blend-difference">
              {{ task.progress }}%
            </span>
          </div>

          <!-- 操作：取消與狀態 -->
          <div class="flex items-center justify-between text-xs mt-1">
            <span class="text-mono-200">
              {{ formatBytes(task.file.size) }}
            </span>
            <button 
              v-if="task.status === 'uploading' || task.status === 'checking'"
              @click="cancelUpload(task.id)"
              class="text-red-400 hover:text-red-300 font-extrabold cursor-pointer border border-transparent hover:border-red-400 px-1.5 py-0.5 rounded transition-all"
            >
              取消
            </button>
            <span v-else-if="task.status === 'finalizing'" class="text-yellow-400 font-extrabold animate-pulse">合併中...</span>
            <span v-else-if="task.status === 'success'" class="text-green-400 font-extrabold">✓ 已完成</span>
            <span v-else-if="task.status === 'failed'" class="text-red-500 font-extrabold">✗ 失敗</span>
            <span v-else-if="task.status === 'canceled'" class="text-mono-300 italic">已取消</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* 滾動條樣式，使其符合粗獷黑白灰色調 */
::-webkit-scrollbar {
  width: 10px;
}
::-webkit-scrollbar-track {
  background: #686666;
}
::-webkit-scrollbar-thumb {
  background: #494949;
  border: 2px solid black;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #121212;
}
</style>
