from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

router = APIRouter()


@router.get("/me")
async def get_current_user():
    """获取当前用户信息"""
    # TODO: 实现获取当前用户逻辑
    return {"user_id": 1, "username": "示例用户", "email": "user@example.com"}


@router.put("/me")
async def update_current_user():
    """更新当前用户信息"""
    # TODO: 实现更新用户逻辑
    return {"message": "用户信息已更新"}
