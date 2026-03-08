"""
Worker 实现模块

各角色的具体实现
"""

from src.core.agent import Agent
from src.core.memory import MemoryManager
from src.skills.skill_manager import SkillManager


class ArchitectWorker(Agent):
    """系统架构师 Worker"""
    
    def __init__(self):
        super().__init__("张建国", "System Architect")
        self.memory = MemoryManager()
        self.skill_manager = SkillManager()
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行架构设计任务"""
        self.memory.add_memory(f"Task: {task}", {"type": "architecture"})
        return f"Architect: 完成 {task} 的架构设计"


class SearchWorker(Agent):
    """搜索 Worker"""
    
    def __init__(self):
        super().__init__("林觅", "Search Worker")
        self.memory = MemoryManager()
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行搜索任务"""
        self.memory.add_memory(f"Search: {task}", {"type": "research"})
        return f"Search: 完成 {task} 的调研"


class ChallengerWorker(Agent):
    """质询 Worker"""
    
    def __init__(self):
        super().__init__("郑思远", "Challenger Worker")
        self.memory = MemoryManager()
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行质询任务"""
        self.memory.add_memory(f"Challenge: {task}", {"type": "review"})
        return f"Challenger: 完成 {task} 的审查"


class DevOpsWorker(Agent):
    """运维 Worker"""
    
    def __init__(self):
        super().__init__("运维", "DevOps Worker")
        self.memory = MemoryManager()
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行运维任务"""
        self.memory.add_memory(f"DevOps: {task}", {"type": "operations"})
        return f"DevOps: 完成 {task}"


class TesterWorker(Agent):
    """测试 Worker"""
    
    def __init__(self):
        super().__init__("测试员", "Tester Worker")
        self.memory = MemoryManager()
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行测试任务"""
        self.memory.add_memory(f"Test: {task}", {"type": "testing"})
        return f"Tester: 完成 {task} 的测试"


def create_worker(role: str) -> Agent:
    """创建 Worker 实例"""
    workers = {
        "architect": ArchitectWorker,
        "search": SearchWorker,
        "challenger": ChallengerWorker,
        "devops": DevOpsWorker,
        "tester": TesterWorker,
    }
    return workers.get(role, ArchitectWorker)()
