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
    async def init_sparse_file(self, upload_id: str, total_size: int) -> None:
        """建立並預先分配實體檔案空間 (Sparse File)"""
        pass

    @abstractmethod
    async def finalize_file(self, upload_id: str) -> Dict[str, Any]:
        """驗證暫存檔案完整性並正式入籍，回傳 {storage_name, size, hash}"""
        pass

    @abstractmethod
    async def save_chunk(self, upload_id: str, offset: int, data: bytes) -> None:
        """依據指定位移量 (offset) 寫入單一暫存分塊"""
        pass

    @abstractmethod
    async def cleanup_temp(self, upload_id: str) -> None:
        """刪除暫存檔案"""
        pass
