"""
记忆管理模块

负责智能体的记忆存储、检索、巩固
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class Memory:
    """记忆数据结构"""
    id: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    importance: float = 1.0
    access_count: int = 0


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, storage_backend: str = "local"):
        self.storage_backend = storage_backend
        self.memories: Dict[str, Memory] = {}
        self.short_term: List[str] = []  # 短期记忆 ID 列表
        self.long_term: List[str] = []   # 长期记忆 ID 列表
    
    def add_memory(self, content: str, metadata: Optional[Dict] = None, 
                   importance: float = 1.0) -> str:
        """添加记忆"""
        memory_id = str(uuid.uuid4())
        memory = Memory(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(),
            importance=importance
        )
        self.memories[memory_id] = memory
        self.short_term.append(memory_id)
        return memory_id
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Memory]:
        """检索记忆 (简化版，后续接入向量数据库)"""
        # TODO: 实现向量检索
        memories = list(self.memories.values())
        return sorted(memories, key=lambda m: m.importance, reverse=True)[:top_k]
    
    def consolidate(self):
        """记忆巩固：短期→长期"""
        # TODO: 实现记忆巩固逻辑
        pass
    
    def forget(self, threshold: float = 0.5):
        """遗忘低重要性记忆"""
        to_remove = [
            mid for mid, m in self.memories.items() 
            if m.importance < threshold and m.access_count == 0
        ]
        for mid in to_remove:
            del self.memories[mid]
            if mid in self.short_term:
                self.short_term.remove(mid)
            if mid in self.long_term:
                self.long_term.remove(mid)
