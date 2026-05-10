from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class Verify2FARequest(BaseModel):
    username: str
    otp_code: str
