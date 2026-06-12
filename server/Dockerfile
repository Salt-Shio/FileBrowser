# 1. 選擇 Python 3.10 精簡版作為地基
FROM python:3.10-slim

# 2. 設定容器內的工作目錄為 /app
WORKDIR /app

# 3. 設定環境變數：讓 Python 輸出直接顯示在 Log 中，不緩衝
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 4. 先複製依賴清單 (為了利用 Docker 快取)
COPY requirements.txt .

# 5. 安裝相依套件
RUN pip install --no-cache-dir -r requirements.txt

# 6. 複製剩餘的程式碼
COPY . .

# 7. 開放 8000 埠口 (僅作為標記)
EXPOSE 8000

# 8. 啟動指令：執行 FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "15"]
