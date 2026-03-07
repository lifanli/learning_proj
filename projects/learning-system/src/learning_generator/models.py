"""
学习记录数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LearningRecord(BaseModel):
    """学习记录模型"""
    
    id: str = Field(..., description="记录 ID")
    task_id: str = Field(..., description="任务 ID")
    worker: str = Field(..., description="Worker 名称")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    # 任务描述
    task_description: str = Field(..., description="任务描述")
    task_background: Optional[str] = Field(None, description="任务背景")
    constraints: Optional[str] = Field(None, description="约束条件")
    
    # 执行过程
    key_decisions: List[dict] = Field(default_factory=list, description="关键决策")
    problems_encountered: List[dict] = Field(default_factory=list, description="遇到的问题")
    
    # 结果评估
    goal_achieved: bool = Field(..., description="是否达成目标")
    quality_score: int = Field(..., ge=1, le=5, description="质量评分 (1-5)")
    time_assessment: str = Field(..., description="时间评估 (提前/按时/延期)")
    
    # 经验教训
    successes: List[str] = Field(default_factory=list, description="成功经验")
    lessons_learned: List[str] = Field(default_factory=list, description="教训反思")
    improvements: List[str] = Field(default_factory=list, description="待改进点")
    
    # 知识标签
    tags: List[str] = Field(default_factory=list, description="知识标签")
    
    # 关联内容
    related_tasks: List[str] = Field(default_factory=list, description="相关任务")
    references: List[str] = Field(default_factory=list, description="参考文档")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "lr-001",
                "task_id": "task-101",
                "worker": "DevOps Engineer",
                "task_description": "需求确认和 KPI 定义",
                "goal_achieved": True,
                "quality_score": 5,
                "time_assessment": "按时",
                "successes": ["Admin 快速确认", "Challenger 审查通过"],
                "lessons_learned": ["需求文档应尽早启动"],
                "tags": ["需求分析", "KPI 定义"]
            }
        }


class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="检索查询")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    filters: Optional[dict] = Field(None, description="过滤条件")


class SearchResponse(BaseModel):
    """检索响应"""
    query: str
    results: List[dict]
    total: int
    latency_ms: float


class RecommendationRequest(BaseModel):
    """推荐请求"""
    task_description: str
    task_type: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=10)


class RecommendationResponse(BaseModel):
    """推荐响应"""
    task_description: str
    recommendations: List[dict]
    confidence: float
