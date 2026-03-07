from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter()


class Course(BaseModel):
    id: int
    title: str
    description: str
    instructor: str


@router.get("/", response_model=List[Course])
async def get_courses():
    """获取课程列表"""
    # TODO: 从数据库查询课程
    return [
        {"id": 1, "title": "Python 入门", "description": "学习 Python 基础", "instructor": "张老师"},
        {"id": 2, "title": "React 开发", "description": "学习 React 框架", "instructor": "李老师"},
    ]


@router.get("/{course_id}")
async def get_course(course_id: int):
    """获取课程详情"""
    # TODO: 从数据库查询课程详情
    return {"id": course_id, "title": "课程详情", "description": "详细描述"}
