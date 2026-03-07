"""
学习记录生成器 - Learning Record Generator

功能:
- 从任务执行中提取结构化经验
- 生成学习记录 (YAML/JSON 格式)
- 自动标签和分类
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LearningRecord(BaseModel):
    """学习记录数据模型"""
    
    task_id: str
    worker: str
    completed_at: datetime
    task_type: str  # devops/frontend/backend/design
    
    # 任务描述
    goal: str  # 目标
    background: str  # 背景
    constraints: Optional[str] = None  # 约束
    
    # 执行过程
    key_decisions: list = []  # 关键决策
    problems_encountered: list = []  # 遇到的问题
    solutions: list = []  # 解决方案
    
    # 结果评估
    goal_achieved: bool  # 是否达成目标
    quality_score: int  # 质量评分 1-5
    time_assessment: str  # 提前/按时/延期
    
    # 经验教训
    successes: list = []  # 成功经验
    lessons: list = []  # 教训反思
    improvements: list = []  # 待改进点
    
    # 知识标签
    tags: list = []  # 技术/问题/解决方案标签
    
    # 关联内容
    related_tasks: list = []
    references: list = []
    code_commits: list = []


class LearningRecordGenerator:
    """学习记录生成器"""
    
    def __init__(self):
        self.records = []
    
    def generate(self, task_data: dict) -> LearningRecord:
        """
        从任务数据生成学习记录
        
        Args:
            task_data: 任务执行数据
            
        Returns:
            LearningRecord: 生成的学习记录
        """
        record = LearningRecord(
            task_id=task_data.get("task_id", ""),
            worker=task_data.get("worker", ""),
            completed_at=datetime.fromisoformat(task_data.get("completed_at", datetime.now().isoformat())),
            task_type=task_data.get("task_type", "general"),
            goal=task_data.get("goal", ""),
            background=task_data.get("background", ""),
            constraints=task_data.get("constraints"),
            key_decisions=task_data.get("key_decisions", []),
            problems_encountered=task_data.get("problems", []),
            solutions=task_data.get("solutions", []),
            goal_achieved=task_data.get("goal_achieved", True),
            quality_score=task_data.get("quality_score", 3),
            time_assessment=task_data.get("time_assessment", "按时"),
            successes=task_data.get("successes", []),
            lessons=task_data.get("lessons", []),
            improvements=task_data.get("improvements", []),
            tags=task_data.get("tags", []),
            related_tasks=task_data.get("related_tasks", []),
            references=task_data.get("references", []),
            code_commits=task_data.get("code_commits", []),
        )
        
        self.records.append(record)
        return record
    
    def to_yaml(self, record: LearningRecord) -> str:
        """导出为 YAML 格式"""
        import yaml
        return yaml.dump(record.model_dump(), allow_unicode=True, default_flow_style=False)
    
    def to_json(self, record: LearningRecord) -> str:
        """导出为 JSON 格式"""
        import json
        return json.dumps(record.model_dump(), ensure_ascii=False, indent=2)


# 示例用法
if __name__ == "__main__":
    generator = LearningRecordGenerator()
    
    # 示例任务数据
    task_data = {
        "task_id": "task-101",
        "worker": "project-director",
        "goal": "需求确认和 KPI 定义",
        "background": "学习智能体系统项目启动",
        "key_decisions": [
            {"decision": "采用分阶段实施", "reason": "降低风险"}
        ],
        "problems": ["Admin 确认延迟"],
        "solutions": ["提供快速决策文档"],
        "successes": ["需求文档 v1.1 完成"],
        "lessons": ["提前准备决策文档可加速审批"],
        "tags": ["需求分析", "项目管理"],
    }
    
    record = generator.generate(task_data)
    print("学习记录生成成功!")
    print(f"任务 ID: {record.task_id}")
    print(f"工人：{record.worker}")
    print(f"目标：{record.goal}")
