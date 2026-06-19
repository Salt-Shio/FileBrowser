from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseStorage(ABC):
    """
    抽象儲存介面 (Strategy Pattern)
    所有實體儲存操作 (本機硬碟、S3、GCS 等) 皆須實作此介面。
    """
    
    @abstractmethod
    def get_full_path(self, storage_name: str) -> str:
        """獲取實體檔案的絕對路徑/URI"""
        pass

    @abstractmethod
    async def exists(self, storage_name: str) -> bool:
        """檢查實體檔案是否存在"""
        pass

    @abstractmethod
    async def delete_file(self, storage_name: str) -> None:
        """物理刪除正式檔案"""
        pass

    @abstractmethod
    async def merge_from_chunks(self, upload_id: str, total_chunks: int) -> Dict[str, Any]:
        """將暫存碎片合併為正式檔案，並回傳 {storage_name, size, hash}"""
        pass

    @abstractmethod
    async def save_chunk(self, upload_id: str, index: int, data: bytes) -> None:
        """寫入單一暫存分塊"""
        pass

    @abstractmethod
    async def list_chunks(self, upload_id: str) -> List[int]:
        """獲取目前已上傳的分塊索引列表"""
        pass

    @abstractmethod
    async def cleanup_temp(self, upload_id: str) -> None:
        """刪除整個暫存分塊目錄"""
        pass
