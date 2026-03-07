"""
测试学习记录生成器
"""
import pytest
from src.learning_generator import LearningRecordGenerator


class TestLearningRecordGenerator:
    """学习记录生成器测试"""
    
    def test_generate_record(self):
        """测试生成学习记录"""
        generator = LearningRecordGenerator()
        
        record = generator.generate(
            task_id="task-101",
            worker="DevOps Engineer",
            task_description="需求确认和 KPI 定义",
            goal_achieved=True,
            quality_score=5,
            time_assessment="按时",
            successes=["Admin 快速确认"],
            lessons_learned=["需求文档应尽早启动"],
            tags=["需求分析", "KPI 定义"],
        )
        
        assert record.task_id == "task-101"
        assert record.worker == "DevOps Engineer"
        assert record.goal_achieved is True
        assert record.quality_score == 5
        assert len(record.successes) == 1
        assert len(record.tags) == 2
    
    def test_get_record(self):
        """测试获取记录"""
        generator = LearningRecordGenerator()
        
        record = generator.generate(
            task_id="task-101",
            worker="DevOps Engineer",
            task_description="测试任务",
            goal_achieved=True,
            quality_score=4,
            time_assessment="按时",
        )
        
        retrieved = generator.get_record(record.id)
        assert retrieved is not None
        assert retrieved.id == record.id
    
    def test_get_records_by_task(self):
        """测试按任务 ID 查询"""
        generator = LearningRecordGenerator()
        
        generator.generate(
            task_id="task-101",
            worker="DevOps Engineer",
            task_description="任务 1",
            goal_achieved=True,
            quality_score=5,
            time_assessment="按时",
        )
        
        generator.generate(
            task_id="task-101",
            worker="Search Worker",
            task_description="任务 2",
            goal_achieved=True,
            quality_score=4,
            time_assessment="按时",
        )
        
        records = generator.get_records_by_task("task-101")
        assert len(records) == 2
    
    def test_get_records_by_worker(self):
        """测试按 Worker 查询"""
        generator = LearningRecordGenerator()
        
        generator.generate(
            task_id="task-101",
            worker="DevOps Engineer",
            task_description="任务 1",
            goal_achieved=True,
            quality_score=5,
            time_assessment="按时",
        )
        
        generator.generate(
            task_id="task-102",
            worker="DevOps Engineer",
            task_description="任务 2",
            goal_achieved=True,
            quality_score=4,
            time_assessment="按时",
        )
        
        records = generator.get_records_by_worker("DevOps Engineer")
        assert len(records) == 2
