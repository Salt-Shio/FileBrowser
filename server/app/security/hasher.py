"""
密碼安全處理模組 (Password Security)
職責：
1. 提供強大的 Argon2id 雜湊演算法
2. 負責密碼的加密 (Hashing) 與驗證 (Verification)
"""
from passlib.context import CryptContext

# 初始化加密上下文，指定使用 argon2 演算法
# passlib 會自動處理 Salt (鹽值) 與 安全參數
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證明文密碼與雜湊值是否吻合
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    將明文密碼轉換為 Argon2id 雜湊值
    """
    return pwd_context.hash(password)
