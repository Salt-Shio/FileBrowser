# 異常處理架構與思維紀錄 (Exception Management Policy)

## 1. 核心哲學：層級分工 (Layered Responsibility)

系統應遵循 **「低層拋出事實，高層決定對策」** 的原則，確保程式碼的健壯性與可維護性。

- **底層 (Service Layer / Logic Layer)**：
  - **職責**：專注於業務邏輯執行與規則檢查。
  - **原則**：**Fail-Fast (快速失敗)**。一旦偵測到不符合業務規則的情況（例如：找不到檔案、名稱重複、權限不足），應立即拋出異常。
  - **禁忌**：嚴禁拋出 `HTTPException`。Service 層應對 Web 框架保持「無知 (Agnostic)」，以確保邏輯能在 CLI 腳本、背景任務或單元測試中被複用。
  - **工具**：使用自定義的業務異常類別（繼承自 `BaseBusinessException`）。

- **高層 (API Layer / Global Handler)**：
  - **職責**：專注於通訊協定轉換與對外介面。
  - **行為**：作為「翻譯官」，捕獲業務異常，並將其轉換為對應的 HTTP 狀態碼與結構化 JSON 回應。

## 2. 實作機制 (Implementation Mechanism)

### 異常類別體系 (`app/core/exceptions.py`)
所有的業務異常都應繼承自一個統一的基類，這使得全域捕獲成為可能。

```python
class BaseBusinessException(Exception):
    """所有業務異常的基類，包含訊息與建議的 HTTP 狀態碼"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
```

### 全域翻譯器 (Global Exception Handler)
透過 FastAPI 的 `exception_handlers` 機制，系統實作了一個全域攔截器：
- **自動識別**：利用 `exc.__class__.__name__` 自動提取異常類別名稱。
- **標準化回傳**：強制所有錯誤回應格式統一，包含 `detail` 與 `error_code`。
- **宣告式註冊**：在 `FastAPI()` 建構子中一次性完成註冊，保持 `main.py` 簡潔。

## 3. 開發者與前端效益

1.  **除錯效率**：異常在錯誤發生的第一時間觸發，Stack Trace 能精確定位問題點，不會被多層傳遞掩蓋。
2.  **前端邏輯穩定**：前端可根據 `error_code` (例如 `"AuthenticationError"`) 撰寫穩定的邏輯分支，而非依賴易變的文字描述 (`detail`)。
3.  **API 乾淨度**：Router 層不需要 `try...except` 區塊，程式碼保持為單純的調用與回傳。

## 4. 擴充指引

當需要增加新的錯誤情境時，開發者只需：
1.  在 `app/core/exceptions.py` 中新增一個繼承自 `BaseBusinessException` 的類別。
2.  在 Service 層的實作地點直接 `raise` 該異常。
3.  **無須修改 API Router 或全域處理器**，系統會自動處理並回傳。
