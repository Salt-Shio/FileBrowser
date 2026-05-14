# Implementation Plan - VFS Step 3.2: 節點更名與搬移 (Rename/Move)

本計畫實作虛擬節點的名稱修改與位置搬移。由於採用全虛擬路徑設計，所有搬移操作均為秒級的資料庫更新。

## Proposed Changes

### [VFS 模組]

#### [MODIFY] [vfs.py](file:///c:/Users/salt/Desktop/Project/FileBrowser/server/app/schemas/vfs.py)
- 定義 `NodeRenameRequest`: `id`, `type` (file/folder), `new_name`。
- 定義 `NodeMoveRequest`: `id`, `type` (file/folder), `target_parent_id` (Optional)。

#### [MODIFY] [vfs_service.py](file:///c:/Users/salt/Desktop/Project/FileBrowser/server/app/services/vfs_service.py)
- 實作 `rename_node(db, owner_id, type, id, new_name)`:
    - 取得節點。
    - 檢查目標目錄下是否已有同名節點。
    - 更新 `name`。
- 實作 `move_node(db, owner_id, type, id, target_parent_id)`:
    - 取得節點與目標父目錄。
    - **防循環檢查**: 確保目標目錄不是該資料夾本身或其子目錄。
    - 檢查目標目錄下命名衝突。
    - 更新 `parent_id` 或 `folder_id`。

#### [MODIFY] [vfs.py](file:///c:/Users/salt/Desktop/Project/FileBrowser/server/app/api/vfs.py)
- 實作 `PATCH /vfs/rename`。
- 實作 `PATCH /vfs/move`。

## Verification Plan

### Manual Verification (User)
1. 重新命名資料夾，確認瀏覽時名稱已變更。
2. 將一個資料夾移入另一個資料夾，確認層級關係正確。
3. 嘗試將資料夾移入自己內部，確認系統會報錯 (防止循環引用)。
4. 嘗試移動到一個不存在的父目錄，確認系統報錯。
