import os
import re
import asyncio
from datetime import datetime
from src.agents.base_agent import BaseAgent
from src.agents.translator_agent import TranslatorAgent
from src.publisher.structure_planner import StructurePlanner
from src.publisher.fact_checker import FactChecker
from src.storage.rag_manager import LightRAGManager
from src.utils.logger import logger


class EditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role_name="总编辑",
            role_instruction=(
                "你是 AI 知识库的总编辑。你的职责是：\n"
                "1. 组织和整理技术知识内容\n"
                "2. 确保内容质量、准确性和可读性\n"
                "3. 规划章节结构，生成专业的 Markdown 文档\n"
                "4. 所有输出必须为中文"
            )
        )
        self.rag = LightRAGManager()
        self.translator = TranslatorAgent()
        self.planner = StructurePlanner()
        self.fact_checker = FactChecker()
        self.kb_root = "knowledge_base"

    async def initialize(self):
        """初始化 RAG 系统"""
        await self.rag.initialize()
        logger.info("总编辑已初始化，RAG 系统就绪")

    async def process_knowledge(self, content: str, source: str, topic: str):
        """
        完整知识处理流水线：
        1. RAG 插入原始内容
        2. 翻译主题和摘要
        3. StructurePlanner 分类
        4. RAG 综合查询
        5. 翻译输出内容
        6. FactChecker 核查
        7. 写入 Markdown 文件
        """
        logger.info(f"开始处理知识 - 来源: {source}, 主题: {topic}")

        # === 第 1 步: 存入 RAG ===
        logger.info("第 1 步: 存入 RAG 知识图谱")
        enriched_text = f"来源: {source}\n主题: {topic}\n\n{content}"
        await self.rag.insert_text(enriched_text)

        # === 第 2 步: 翻译主题和内容摘要 ===
        logger.info("第 2 步: 翻译主题和内容摘要")
        translated_topic = self.translator.translate(topic)
        content_summary = content[:800]
        translated_summary = self.translator.translate(content_summary)

        # === 第 3 步: 目录规划 ===
        logger.info("第 3 步: 目录分类规划")
        target_dir = self.planner.plan(translated_topic, translated_summary)
        logger.info(f"内容归入分类: {target_dir}")

        # 确保目标目录存在
        dir_path = os.path.join(self.kb_root, target_dir)
        os.makedirs(dir_path, exist_ok=True)

        # === 第 4 步: RAG 综合查询 ===
        logger.info("第 4 步: RAG 综合查询，获取关联知识")
        query = f"请综合介绍关于「{translated_topic}」的技术细节，包括核心概念、关键关系和最新进展。"
        rag_content = await self.rag.query(query, mode="hybrid")

        # === 第 5 步: 翻译 RAG 输出 ===
        logger.info("第 5 步: 翻译综合内容")
        rag_content = rag_content or ""
        translated_rag = self.translator.translate(rag_content) if rag_content else ""

        # === 第 6 步: 生成最终文档内容 ===
        logger.info("第 6 步: 生成编辑后的文档")
        final_content = self._compose_article(
            translated_topic, translated_rag, source, translated_summary
        )

        # === 第 7 步: 事实核查 ===
        logger.info("第 7 步: 事实核查")
        check_result = self.fact_checker.check(final_content, source, rag_content or "")

        if not check_result["passed"]:
            logger.warning(f"事实核查发现问题: {check_result['issues']}")
            final_content = check_result["corrected_content"]
        else:
            logger.info("事实核查通过")

        # === 第 8 步: 写入文件 ===
        logger.info("第 8 步: 写入 Markdown 文件")
        # 文件名清理：移除换行、Windows 非法字符、Markdown 语法残留
        safe_topic = translated_topic.replace("\n", " ").replace("\r", " ")
        safe_topic = re.sub(r'^[\s\-#=]+', '', safe_topic)   # 去掉开头的 ---、###、=== 等
        safe_topic = re.sub(r'[\s\-#=]+$', '', safe_topic)   # 去掉末尾的
        # 替换 Windows 文件名非法字符
        for ch in r'\/:*?"<>|':
            safe_topic = safe_topic.replace(ch, "_")
        # 压缩连续空格和下划线
        safe_topic = re.sub(r'[_\s]+', ' ', safe_topic).strip()[:50]
        if not safe_topic:
            safe_topic = "未命名文章"

        filename = f"{safe_topic}.md"
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        logger.info(f"知识已写入: {file_path}")
        return file_path

    def _compose_article(self, topic: str, rag_content: str, source: str, summary: str) -> str:
        """使用 LLM 编排最终文章"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        rag_content = rag_content or ""
        summary = summary or ""

        rag_section = rag_content[:3000] if rag_content else "（暂无 RAG 检索结果）"

        prompt = f"""请根据以下素材，编写一篇结构化的中文技术文章。要求：
1. 使用 Markdown 格式
2. 包含标题、概述、核心内容、总结和参考来源
3. 语言专业流畅
4. 关键技术术语可保留英文
5. 内容中已包含 Markdown 图片引用 `![](url)`，请在合适的位置保留这些图片引用，不要移除或修改图片链接

主题: {topic}
来源: {source}
时间: {now}

内容摘要:
{summary}

RAG 知识图谱检索结果:
{rag_section}

请直接输出完整的 Markdown 文章:"""

        result = self.chat(prompt, stream=False)
        if result and not result.startswith("Error:"):
            return result

        # LLM 调用失败时的回退模板
        return f"""# {topic}

> 更新时间: {now} | 来源: {source}

## 概述
{summary}

## 详细内容
{rag_content or "暂无详细内容"}

## 参考来源
- {source}
"""
