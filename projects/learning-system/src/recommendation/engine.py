"""
智能推荐引擎
"""
from typing import List, Dict, Any
from datetime import datetime
import re


class RecommendationEngine:
    """智能推荐引擎（基于关键词匹配，后续替换为向量检索）"""
    
    def __init__(self):
        self.records = []
    
    def add_record(self, record_data: Dict[str, Any]):
        """添加记录到推荐池"""
        self.records.append(record_data)
    
    def recommend(
        self,
        task_description: str,
        task_type: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        推荐相似任务
        
        Args:
            task_description: 任务描述
            task_type: 任务类型 (可选)
            top_k: 推荐数量
        
        Returns:
            List[Dict]: 推荐结果列表
        """
        scores = []
        
        for record in self.records:
            score = self._calculate_similarity(
                task_description,
                record.get("task_description", ""),
                record.get("tags", [])
            )
            
            if score > 0:
                scores.append({
                    "record": record,
                    "score": score,
                    "reason": self._generate_reason(score, record)
                })
        
        # 按分数排序
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
    
    def _calculate_similarity(
        self,
        query: str,
        target: str,
        tags: List[str]
    ) -> float:
        """计算相似度"""
        score = 0.0
        
        # 关键词匹配
        query_words = set(query.lower().split())
        target_words = set(target.lower().split())
        
        # 重叠词
        overlap = query_words & target_words
        if overlap:
            score += len(overlap) * 0.3
        
        # 标签匹配
        for tag in tags:
            if tag.lower() in query_words:
                score += 0.2
        
        return score
    
    def _generate_reason(self, score: float, record: Dict[str, Any]) -> str:
        """生成推荐理由"""
        if score >= 0.8:
            return "高度相似，强烈推荐参考"
        elif score >= 0.5:
            return "中度相似，有参考价值"
        else:
            return "低度相似，仅供参考"
    
    def clear(self):
        """清空推荐池"""
        self.records = []
