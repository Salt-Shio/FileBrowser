"""
虛擬檔案系統 API 路由 (VFS Endpoints)
職責：
1. 提供目錄瀏覽功能 (/ls)
2. 提供檔案搜尋功能 (/search)
3. 整合身分驗證，確保使用者只能存取自己的檔案
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile, status

from app.api import deps
from app.api.responses import MonitoredFileResponse
from app.services.vfs_service import VFSService
from app import schemas
from app.models import User
from app.core.exceptions import NodeNotFoundError

router = APIRouter()

@router.get("/ls", response_model=schemas.vfs.BrowseResponse)
async def list_directory(
    folder_id: Optional[str] = Query(None, description="要瀏覽的資料夾 UUID，若為空則顯示根目錄"),
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    獲取指定目錄的內容，包含子資料夾、檔案與導航麵包屑。
    """
    return await service.get_browse_data(folder_id, current_user.id)


@router.get("/search", response_model=schemas.vfs.SearchResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, description="搜尋關鍵字"),
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    模糊搜尋使用者擁有的所有資料夾與檔案。
    """
    return await service.search_nodes(current_user.id, q)

@router.post("/mkdir", response_model=schemas.vfs.FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: schemas.vfs.FolderCreate,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    建立新的虛擬資料夾。
    """
    return await service.create_folder(
        current_user.id, 
        data.name, 
        data.parent_id
    )

@router.post("/rename")
async def rename_node(
    data: schemas.vfs.NodeRenameRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    重新命名資料夾或檔案。
    """
    return await service.rename_node(
        current_user.id,
        data.node_id,
        data.node_type,
        data.new_name
    )

@router.post("/move")
async def move_node(
    data: schemas.vfs.NodeMoveRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    搬移資料夾或檔案到指定目錄。
    """
    return await service.move_node(
        current_user.id,
        data.node_id,
        data.node_type,
        data.target_parent_id
    )

@router.post("/delete")
async def delete_node(
    data: schemas.vfs.NodeDeleteRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    邏輯刪除資料夾或檔案 (Explicit Action)。
    """
    return await service.delete_node(
        current_user.id,
        data.node_id,
        data.node_type
    )


@router.post("/upload/init", response_model=schemas.vfs.UploadInitResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(
    data: schemas.vfs.UploadInitRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    初始化分塊上傳會話 (Step 4.3 第一階段)。
    """
    session, uploaded_chunks = await service.init_upload(
        filename=data.filename,
        total_size=data.total_size,
        chunk_size=data.chunk_size,
        last_modified=data.last_modified,
        owner_id=current_user.id,
        target_folder_id=data.target_folder_id
    )
    return {
        "upload_id": session.id,
        "filename": session.filename,
        "total_chunks": session.total_chunks,
        "upload_token": session.upload_token,
        "uploaded_chunks": uploaded_chunks
    }


@router.post("/upload/chunk", response_model=schemas.vfs.UploadChunkResponse)
async def upload_chunk(
    upload_id: str = Form(..., description="上傳會話 UUID"),
    chunk_index: int = Form(..., description="分塊索引號 (0 起始)"),
    upload_token: str = Form(..., description="會話防護金鑰"),
    file: UploadFile = File(..., description="分塊二進制數據"),
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    上傳分塊資料暫存至磁碟暫存目錄 (Step 4.3 第二階段)。
    """
    # 讀取二進制內容
    chunk_data = await file.read()
    await service.upload_chunk(
        upload_id=upload_id,
        chunk_index=chunk_index,
        upload_token=upload_token,
        chunk_data=chunk_data,
        owner_id=current_user.id
    )
    return {
        "message": "分塊上傳成功",
        "chunk_index": chunk_index
    }


@router.post("/upload/resume", response_model=schemas.vfs.UploadStatusResponse)
async def resume_upload(
    data: schemas.vfs.UploadResumeRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
) -> schemas.vfs.UploadStatusResponse:
    """
    發起斷點續傳，驗證檔案特徵並獲取進度狀態與缺失分塊。
    """
    return await service.resume_upload(
        upload_id=data.upload_id,
        owner_id=current_user.id,
        target_folder_id=data.target_folder_id,
        last_modified=data.last_modified
    )


@router.post("/upload/cancel", response_model=schemas.vfs.UploadCancelResponse)
async def cancel_upload(
    data: schemas.vfs.UploadCancelRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
) -> schemas.vfs.UploadCancelResponse:
    """
    主動取消上傳會話，立即清除所有資料庫紀錄與磁碟暫存分塊碎片。
    """
    return await service.cancel_upload(
        upload_id=data.upload_id,
        owner_id=current_user.id
    )


@router.post("/upload/finalize", response_model=schemas.vfs.FileResponse)
async def finalize_upload(
    data: schemas.vfs.UploadFinalizeRequest,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    物理合併分塊、校驗 Hash、虛擬入籍、並清理會話與碎片 (Step 4.3 第三階段)。
    """
    return await service.finalize_upload(
        upload_id=data.upload_id,
        owner_id=current_user.id,
        upload_token=data.upload_token
    )


@router.post("/download/ticket/{file_id}")
async def get_download_ticket(
    file_id: str,
    service: VFSService = Depends(deps.get_vfs_service),
    current_user: User = Depends(deps.get_current_user)
):
    """
    為指定檔案生成一個 30 秒有效的臨時下載 Ticket。
    30 秒內對同一使用者與同一檔案重複申請，回傳相同的 Ticket。
    """
    ticket = await service.create_download_ticket(
        file_id=file_id,
        owner_id=current_user.id
    )
    return {"ticket": ticket}


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    ticket: str = Query(..., description="臨時下載憑證"),
    service: VFSService = Depends(deps.get_vfs_service)
) -> MonitoredFileResponse:
    """
    使用臨時憑證進行下載，限制 30 秒內最多發起 4 次請求。
    不需要 JWT 驗證，憑證本身即為授權依據。
    """
    # 1. 呼叫服務層進行憑證校驗、連線數判定與檔案擁有權檢查
    file_obj = await service.verify_and_prepare_download(
        file_id=file_id,
        ticket=ticket
    )

    # 2. 取得絕對實體路徑
    physical_path = service.storage.get_full_path(file_obj.storage_path)

    # 3. 封裝快取校驗標頭
    headers = {
        "ETag": f'"{file_obj.hash_sha256}"'
    }

    # 4. 回傳自訂的 MonitoredFileResponse 監控連線
    return MonitoredFileResponse(
        path=physical_path,
        filename=file_obj.name,
        media_type=file_obj.mime_type or "application/octet-stream",
        headers=headers
    )
