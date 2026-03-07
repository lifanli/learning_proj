"""
学习智能体系统 - 主入口

Usage:
    python -m learning_agent
"""

from src.core import Agent, MemoryManager, create_vector_db
from src.skills import SkillManager
from src.learning import ReflectionSystem, LearningOptimizer


def main():
    """主函数"""
    print("学习智能体系统 v0.1.0")
    print("=" * 40)
    
    # 初始化核心组件
    memory = MemoryManager()
    vector_db = create_vector_db("local")
    vector_db.connect({})
    skill_manager = SkillManager()
    reflection = ReflectionSystem()
    optimizer = LearningOptimizer()
    
    print("✓ 核心组件初始化完成")
    print(f"  - Memory Manager: {memory}")
    print(f"  - Vector DB: {vector_db}")
    print(f"  - Skill Manager: {skill_manager}")
    print(f"  - Reflection System: {reflection}")
    print(f"  - Learning Optimizer: {optimizer}")
    
    # 注册内置技能
    from src.skills.builtin import read_file, write_file, web_search
    
    skill_manager.register("read_file", read_file, "读取文件内容")
    skill_manager.register("write_file", write_file, "写入文件")
    skill_manager.register("web_search", web_search, "网络搜索")
    
    print("✓ 内置技能注册完成")
    print(f"  可用技能：{skill_manager.list_skills()}")
    
    # 测试向量数据库
    test_vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    test_metadata = [{"text": "test1"}, {"text": "test2"}]
    ids = vector_db.insert(test_vectors, test_metadata)
    print(f"✓ 向量数据库测试完成 (插入 {len(ids)} 条)")
    
    print("=" * 40)
    print("系统就绪!")


if __name__ == "__main__":
    main()
