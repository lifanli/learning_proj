"""
技能管理器

负责技能的注册、发现、调用
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass


@dataclass
class SkillDefinition:
    """技能定义"""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any]


class SkillManager:
    """技能管理器"""
    
    def __init__(self):
        self.skills: Dict[str, SkillDefinition] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register(self, name: str, func: Callable, 
                 description: str = "", parameters: Optional[Dict] = None,
                 category: Optional[str] = None):
        """注册技能"""
        skill = SkillDefinition(
            name=name,
            description=description,
            func=func,
            parameters=parameters or {}
        )
        self.skills[name] = skill
        
        if category:
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(name)
    
    def get(self, name: str) -> Optional[SkillDefinition]:
        """获取技能"""
        return self.skills.get(name)
    
    def execute(self, name: str, **kwargs) -> Any:
        """执行技能"""
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")
        return skill.func(**kwargs)
    
    def list_skills(self, category: Optional[str] = None) -> List[str]:
        """列出所有技能"""
        if category:
            return self.categories.get(category, [])
        return list(self.skills.keys())
    
    def discover(self, capability: str) -> List[SkillDefinition]:
        """根据能力需求发现技能"""
        # TODO: 实现智能技能发现
        return [s for s in self.skills.values() if capability.lower() in s.description.lower()]
