"""
知识库存储模块
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


class KnowledgeStorage:
    """知识库存储（内存实现，后续替换为向量数据库）"""
    
    def __init__(self):
        self.records = {}
        self.index = {}  # 简单关键词索引
    
    def store(self, record_id: str, record_data: Dict[str, Any]) -> bool:
        """
        存储学习记录
        
        Args:
            record_id: 记录 ID
            record_data: 记录数据
        
        Returns:
            bool: 是否成功
        """
        try:
            self.records[record_id] = {
                "data": record_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            # 建立简单索引
            self._build_index(record_id, record_data)
            return True
        except Exception as e:
            print(f"存储失败：{e}")
            return False
    
    def retrieve(self, record_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 检索记录"""
        if record_id in self.records:
            return self.records[record_id]["data"]
        return None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索记录（简单关键词匹配，后续替换为向量检索）
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
        
        Returns:
            List[Dict]: 搜索结果列表
        """
        results = []
        query_lower = query.lower()
        
        for record_id, record in self.records.items():
            data = record["data"]
            score = 0
            
            # 简单关键词匹配
            searchable_fields = [
                data.get("task_description", ""),
                data.get("task_background", ""),
                " ".join(data.get("tags", [])),
                " ".join(data.get("successes", [])),
                " ".join(data.get("lessons_learned", [])),
            ]
            
            for text in searchable_fields:
                if query_lower in text.lower():
                    score += 1
            
            if score > 0:
                results.append({
                    "record_id": record_id,
                    "data": data,
                    "score": score,
                    "created_at": record["created_at"],
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _build_index(self, record_id: str, record_data: Dict[str, Any]):
        """建立简单关键词索引"""
        tags = record_data.get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in self.index:
                self.index[tag_lower] = []
            self.index[tag_lower].append(record_id)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有记录"""
        return [
            {"record_id": rid, "data": r["data"], "created_at": r["created_at"]}
            for rid, r in self.records.items()
        ]
    
    def count(self) -> int:
        """获取记录总数"""
        return len(self.records)
    
    def delete(self, record_id: str) -> bool:
        """删除记录"""
        if record_id in self.records:
            del self.records[record_id]
            return True
        return False
