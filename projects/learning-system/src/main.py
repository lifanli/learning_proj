"""
学习智能体系统 - 主入口

FastAPI 应用，提供 RESTful API
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from src.learning_generator import LearningRecord, LearningRecordGenerator
from src.knowledge_base import KnowledgeBase

app = FastAPI(
    title="学习智能体系统",
    description="经验沉淀与知识复用系统",
    version="0.1.0",
)

# 初始化组件
generator = LearningRecordGenerator()
knowledge_base = KnowledgeBase()


class TaskData(BaseModel):
    """任务数据输入模型"""
    task_id: str
    worker: str
    goal: str
    background: str
    key_decisions: Optional[List[dict]] = []
    problems: Optional[List[str]] = []
    solutions: Optional[List[str]] = []
    successes: Optional[List[str]] = []
    lessons: Optional[List[str]] = []
    tags: Optional[List[str]] = []


@app.get("/")
def read_root():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/learning-records/", response_model=LearningRecord)
def create_learning_record(task_data: TaskData):
    """
    创建学习记录
    
    - **task_id**: 任务 ID
    - **worker**: 执行 Worker
    - **goal**: 任务目标
    - **background**: 任务背景
    - **key_decisions**: 关键决策
    - **problems**: 遇到的问题
    - **solutions**: 解决方案
    - **successes**: 成功经验
    - **lessons**: 教训反思
    - **tags**: 知识标签
    """
    record = generator.generate(task_data.model_dump())
    knowledge_base.store(record.model_dump())
    return record


@app.get("/learning-records/")
def list_learning_records(limit: int = 10):
    """获取学习记录列表"""
    return generator.records[:limit]


@app.get("/knowledge-base/search")
def search_knowledge(query: str, top_k: int = 5):
    """
    搜索知识库
    
    - **query**: 搜索查询
    - **top_k**: 返回结果数量
    """
    results = knowledge_base.search(query, top_k)
    return {"query": query, "results": results, "count": len(results)}


@app.get("/knowledge-base/stats")
def get_knowledge_base_stats():
    """获取知识库统计信息"""
    return knowledge_base.get_stats()


@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "learning_records": len(generator.records),
        "knowledge_base_size": len(knowledge_base.records),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
