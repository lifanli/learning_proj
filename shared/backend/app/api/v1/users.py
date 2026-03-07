from fastapi import APIRouter
router = APIRouter()

@router.get("/me")
async def get_current_user():
    """获取当前用户信息"""
    return {"user_id": 1, "username": "示例用户", "email": "user@example.com"}
