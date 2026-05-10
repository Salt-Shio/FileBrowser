"""
真實 IP 辨識中間件 (Real IP Middleware)
職責：
1. 辨識請求是否來自 Cloudflare
2. 提取 CF-Connecting-IP 並將其設為真實訪客 IP
3. 將結果存入 request.state.real_ip 供後續邏輯使用
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RealIPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 嘗試從 Cloudflare 標頭抓取真實 IP
        real_ip = request.headers.get("cf-connecting-ip")
        
        # 2. 如果沒有 CF 標頭，就退而求其次抓直接連線的 IP
        if not real_ip:
            real_ip = request.client.host
        
        # 3. 將真實 IP 存入 request.state，方便之後在 API 裡調用
        request.state.real_ip = real_ip
        
        # 4. 繼續執行後續的請求
        response = await call_next(request)
        return response
