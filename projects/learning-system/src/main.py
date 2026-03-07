"""
学习智能体系统 - FastAPI 主应用
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List

from .learning_generator import LearningRecordGenerator
from .knowledge_base import KnowledgeStorage
from .learning_generator.models import (
    LearningRecord,
    SearchRequest,
    SearchResponse,
    RecommendationRequest,
    RecommendationResponse,
)

app = FastAPI(
    title="学习智能体系统",
    description="经验沉淀与知识复用系统",
    version="0.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
generator = LearningRecordGenerator()
storage = KnowledgeStorage()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "records_count": storage.count(),
    }


@app.post("/api/learning-records", response_model=LearningRecord, tags=["学习记录"])
async def create_learning_record(record: LearningRecord):
    """
    创建学习记录
    
    - **task_id**: 任务 ID
    - **worker**: Worker 名称
    - **task_description**: 任务描述
    - **goal_achieved**: 是否达成目标
    - **quality_score**: 质量评分 (1-5)
    """
    try:
        # 存储到知识库
        storage.store(record.id, record.dict())
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败：{e}")


@app.get("/api/learning-records", response_model=List[LearningRecord], tags=["学习记录"])
async def list_learning_records(task_id: str = None, worker: str = None):
    """
    查询学习记录
    
    - **task_id**: 按任务 ID 过滤 (可选)
    - **worker**: 按 Worker 过滤 (可选)
    """
    try:
        if task_id:
            records = generator.get_records_by_task(task_id)
        elif worker:
            records = generator.get_records_by_worker(worker)
        else:
            records = generator.get_all_records()
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{e}")


@app.post("/api/search", response_model=SearchResponse, tags=["检索"])
async def search_knowledge(request: SearchRequest):
    """
    知识库检索
    
    - **query**: 检索查询
    - **top_k**: 返回结果数量 (默认 5)
    """
    try:
        start_time = datetime.utcnow()
        results = storage.search(request.query, request.top_k)
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            latency_ms=latency,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败：{e}")


@app.post("/api/recommend", response_model=RecommendationResponse, tags=["推荐"])
async def get_recommendations(request: RecommendationRequest):
    """
    获取推荐
    
    - **task_description**: 任务描述
    - **task_type**: 任务类型 (可选)
    - **top_k**: 推荐数量 (默认 5)
    """
    # TODO: 实现推荐算法
    return RecommendationResponse(
        task_description=request.task_description,
        recommendations=[],
        confidence=0.0,
    )


@app.get("/api/stats", tags=["统计"])
async def get_stats():
    """获取系统统计信息"""
    return {
        "total_records": storage.count(),
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
