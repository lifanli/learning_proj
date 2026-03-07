"""
学习记录生成器
"""
from datetime import datetime
from typing import List, Optional
import uuid

from .models import LearningRecord


class LearningRecordGenerator:
    """学习记录生成器"""
    
    def __init__(self):
        self.records = []
    
    def generate(
        self,
        task_id: str,
        worker: str,
        task_description: str,
        goal_achieved: bool,
        quality_score: int,
        time_assessment: str,
        task_background: Optional[str] = None,
        constraints: Optional[str] = None,
        key_decisions: Optional[List[dict]] = None,
        problems_encountered: Optional[List[dict]] = None,
        successes: Optional[List[str]] = None,
        lessons_learned: Optional[List[str]] = None,
        improvements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        related_tasks: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
    ) -> LearningRecord:
        """
        生成学习记录
        
        Args:
            task_id: 任务 ID
            worker: Worker 名称
            task_description: 任务描述
            goal_achieved: 是否达成目标
            quality_score: 质量评分 (1-5)
            time_assessment: 时间评估
            task_background: 任务背景 (可选)
            constraints: 约束条件 (可选)
            key_decisions: 关键决策 (可选)
            problems_encountered: 遇到的问题 (可选)
            successes: 成功经验 (可选)
            lessons_learned: 教训反思 (可选)
            improvements: 待改进点 (可选)
            tags: 知识标签 (可选)
            related_tasks: 相关任务 (可选)
            references: 参考文档 (可选)
        
        Returns:
            LearningRecord: 生成的学习记录
        
        Example:
            >>> generator = LearningRecordGenerator()
            >>> record = generator.generate(
            ...     task_id="task-101",
            ...     worker="DevOps Engineer",
            ...     task_description="需求确认和 KPI 定义",
            ...     goal_achieved=True,
            ...     quality_score=5,
            ...     time_assessment="按时",
            ...     successes=["Admin 快速确认"],
            ...     lessons_learned=["需求文档应尽早启动"],
            ...     tags=["需求分析", "KPI 定义"]
            ... )
        """
        record = LearningRecord(
            id=f"lr-{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            worker=worker,
            task_description=task_description,
            task_background=task_background,
            constraints=constraints,
            key_decisions=key_decisions or [],
            problems_encountered=problems_encountered or [],
            goal_achieved=goal_achieved,
            quality_score=quality_score,
            time_assessment=time_assessment,
            successes=successes or [],
            lessons_learned=lessons_learned or [],
            improvements=improvements or [],
            tags=tags or [],
            related_tasks=related_tasks or [],
            references=references or [],
        )
        
        self.records.append(record)
        return record
    
    def get_record(self, record_id: str) -> Optional[LearningRecord]:
        """根据 ID 获取学习记录"""
        for record in self.records:
            if record.id == record_id:
                return record
        return None
    
    def get_all_records(self) -> List[LearningRecord]:
        """获取所有学习记录"""
        return self.records
    
    def get_records_by_task(self, task_id: str) -> List[LearningRecord]:
        """根据任务 ID 获取学习记录"""
        return [r for r in self.records if r.task_id == task_id]
    
    def get_records_by_worker(self, worker: str) -> List[LearningRecord]:
        """根据 Worker 获取学习记录"""
        return [r for r in self.records if r.worker == worker]
    
    def clear(self):
        """清空所有记录"""
        self.records = []
