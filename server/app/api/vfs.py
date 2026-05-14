"""
虛擬檔案系統 API 路由 (VFS Endpoints)
職責：
1. 提供目錄瀏覽功能 (/ls)
2. 提供檔案搜尋功能 (/search)
3. 整合身分驗證，確保使用者只能存取自己的檔案
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.vfs_service import VFSService
from app import schemas
from app.models import User

router = APIRouter()

@router.get("/ls", response_model=schemas.vfs.BrowseResponse)
async def list_directory(
    folder_id: Optional[str] = Query(None, description="要瀏覽的資料夾 UUID，若為空則顯示根目錄"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    獲取指定目錄的內容，包含子資料夾、檔案與導航麵包屑。
    """
    # 1. 決定目標資料夾
    if folder_id is None:
        # 使用者未指定 ID，獲取或建立其根目錄
        current_folder = await VFSService.get_or_create_root(db, current_user.id)
        target_id = current_folder.id
    else:
        # 使用者指定了 ID，從資料庫查詢並驗證權限
        current_folder = await VFSService.get_folder_by_id(db, folder_id, current_user.id)
        if not current_folder:
            from app.core.exceptions import NodeNotFoundError
            raise NodeNotFoundError("資料夾不存在或無權限存取")
        target_id = current_folder.id

    # 2. 獲取該目錄下的詳細內容
    browse_data = await VFSService.get_browse_data(db, target_id, current_user.id)

    # 3. 封裝回傳內容 (對齊 BrowseResponse Schema)
    return {
        "current_folder": current_folder,
        "breadcrumbs": browse_data["breadcrumbs"],
        "subfolders": browse_data["folders"],
        "files": browse_data["files"]
    }

@router.get("/search", response_model=schemas.vfs.SearchResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, description="搜尋關鍵字"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    模糊搜尋使用者擁有的所有資料夾與檔案。
    """
    return await VFSService.search_nodes(db, current_user.id, q)

@router.post("/mkdir", response_model=schemas.vfs.FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: schemas.vfs.FolderCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    建立新的虛擬資料夾。
    """
    return await VFSService.create_folder(
        db, 
        current_user.id, 
        data.name, 
        data.parent_id
    )

@router.post("/rename")
async def rename_node(
    data: schemas.vfs.NodeRenameRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    重新命名資料夾或檔案。
    """
    return await VFSService.rename_node(
        db,
        current_user.id,
        data.node_id,
        data.node_type,
        data.new_name
    )

@router.post("/move")
async def move_node(
    data: schemas.vfs.NodeMoveRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    搬移資料夾或檔案到指定目錄。
    """
    return await VFSService.move_node(
        db,
        current_user.id,
        data.node_id,
        data.node_type,
        data.target_parent_id
    )

@router.post("/delete")
async def delete_node(
    data: schemas.vfs.NodeDeleteRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    邏輯刪除資料夾或檔案 (Explicit Action)。
    """
    return await VFSService.delete_node(
        db,
        current_user.id,
        data.node_id,
        data.node_type
    )
