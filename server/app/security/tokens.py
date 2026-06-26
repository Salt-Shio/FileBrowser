"""
Token 生成器模組
職責：負責生成各種具備密碼學安全強度的亂數 Token (例如 Fencing Token)。
"""
import secrets

def generate_fencing_token() -> str:
    """
    生成具有密碼學安全強度的隨機 Token。
    可用於 Session Takeover (會話接管) 或防止重放攻擊的 Fencing Token。
    回傳長度約 43 個字元的 URL Safe 字串。
    """
    return secrets.token_urlsafe(32)
