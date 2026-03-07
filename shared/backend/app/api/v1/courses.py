from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

router = APIRouter()

class Course(BaseModel):
    id: int
    title: str
    description: str

@router.get("/", response_model=List[Course])
async def get_courses():
    """获取课程列表"""
    return [
        {"id": 1, "title": "Python 入门", "description": "学习 Python 基础"},
        {"id": 2, "title": "Vue3 开发", "description": "学习 Vue3 框架"},
    ]
