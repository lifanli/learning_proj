"""
智能体基类

所有 Worker Agent 的基类，提供通用功能
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class Agent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.created_at = datetime.now()
        self.memory: Optional[Any] = None
        self.skills: Dict[str, Any] = {}
    
    @abstractmethod
    def execute(self, task: str, context: Optional[Dict] = None) -> Any:
        """执行任务"""
        pass
    
    def register_skill(self, name: str, skill: Any):
        """注册技能"""
        self.skills[name] = skill
    
    def get_skill(self, name: str) -> Optional[Any]:
        """获取技能"""
        return self.skills.get(name)
    
    def __repr__(self):
        return f"Agent(name={self.name}, role={self.role})"
