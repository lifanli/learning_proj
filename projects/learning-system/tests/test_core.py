"""
学习智能体系统 - 测试模块
"""

import unittest
from src.core.agent import Agent
from src.core.memory import MemoryManager, Memory
from src.skills.skill_manager import SkillManager


class TestAgent(unittest.TestCase):
    """测试 Agent 基类"""
    
    def test_agent_creation(self):
        """测试 Agent 创建"""
        class TestAgentImpl(Agent):
            def execute(self, task, context=None):
                return f"Executing: {task}"
        
        agent = TestAgentImpl("test", "tester")
        self.assertEqual(agent.name, "test")
        self.assertEqual(agent.role, "tester")
    
    def test_skill_registration(self):
        """测试技能注册"""
        class TestAgentImpl(Agent):
            def execute(self, task, context=None):
                return task
        
        agent = TestAgentImpl("test", "tester")
        agent.register_skill("test_skill", lambda x: x * 2)
        self.assertIn("test_skill", agent.skills)


class TestMemoryManager(unittest.TestCase):
    """测试记忆管理"""
    
    def test_add_memory(self):
        """测试添加记忆"""
        mm = MemoryManager()
        memory_id = mm.add_memory("test content", {"key": "value"})
        self.assertIn(memory_id, mm.memories)
    
    def test_retrieve_memory(self):
        """测试检索记忆"""
        mm = MemoryManager()
        mm.add_memory("content 1", importance=1.0)
        mm.add_memory("content 2", importance=2.0)
        mm.add_memory("content 3", importance=3.0)
        
        results = mm.retrieve("test", top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].importance, 3.0)


class TestSkillManager(unittest.TestCase):
    """测试技能管理"""
    
    def test_register_skill(self):
        """测试注册技能"""
        sm = SkillManager()
        sm.register("test", lambda x: x, "test skill")
        self.assertIn("test", sm.skills)
    
    def test_execute_skill(self):
        """测试执行技能"""
        sm = SkillManager()
        sm.register("add", lambda a, b: a + b, "addition")
        result = sm.execute("add", a=2, b=3)
        self.assertEqual(result, 5)


if __name__ == "__main__":
    unittest.main()
