from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    # TODO: 从数据库查询用户
    # 示例实现
    if request.email == "test@example.com" and request.password == "test123":
        access_token = create_access_token(data={"sub": request.email})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="邮箱或密码错误")

@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册"""
    return {"message": "注册成功"}
