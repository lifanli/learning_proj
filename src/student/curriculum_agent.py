"""
课程规划智能体 (CurriculumAgent)
=================================
给定一个学习方向（如"LLM全栈"），用 LLM 生成完整的结构化课程表，
匹配预置优质资源，输出 curriculum.yaml 供用户审核。
流程：
1. LLM 生成 领域->主题 的结构
2. 匹配 CurriculumRegistry 预置源，自动填充 known_sources
3. 写入 config/curriculum.yaml，状态=draft
4. 用户审核/修正 -> 状态变为 approved
5. StudentAgent.study_curriculum() 按计划自动执行
"""

import os
import re
import time
from typing import Dict, List, Optional

import yaml

from src.core.progress import raise_if_cancel_requested, report_progress
from src.core.worker import BaseWorker, WorkerInput, WorkerOutput, WorkerSpec
from src.utils.logger import logger


CURRICULUM_PATH = "config/curriculum.yaml"
REGISTRY_PATH = "config/curriculum_registry.yaml"
CURRICULUM_DEBUG_DIR = "logs/curriculum"
CURRICULUM_SYSTEM_PROMPT = (
    "你是AI教育课程设计专家。请严格按YAML格式输出课程表结构，不要输出YAML以外的内容。"
)


def _build_curriculum_prompt(goal: str, depth: str) -> str:
    topic_range = {
        "quick": "5-10",
        "comprehensive": "15-25",
        "expert": "30-50",
    }.get(depth, "15-25")

    return f"""你是一位资深的AI教育专家。请为以下学习方向设计一份系统的课程表。
学习方向: {goal}
要求的主题数量: {topic_range}个主题
请设计一份结构化课程表，包含：
1. 多个学习领域（domain），每个领域包含多个具体主题（topic）
2. 领域按学习顺序排列（priority: 1=最先学，数字越大越后学）
3. 每个主题附带3-4个搜索关键词，必须同时包含中文和英文关键词（用于搜索中英文资料）
4. 每个主题标注难度: beginner / intermediate / advanced
5. 覆盖理论 -> 实践 -> 工程 -> 前沿的完整路径

请严格按以下YAML格式输出（不要输出其他内容）：
```yaml
domains:
  - name: "领域名称"
    priority: 1
    description: "领域简介"
    topics:
      - name: "主题名称"
        status: pending
        difficulty: beginner
        description: "一句话描述这个主题要学什么"
        search_queries:
          - "Transformer architecture tutorial"
          - "Transformer 架构 教程"
          - "attention mechanism explained"
          - "注意力机制 详解"
        known_sources: []
        discovered_sources: []
      - name: "主题名称2"
        status: pending
        difficulty: intermediate
        description: "..."
        search_queries:
          - "English keyword 1"
          - "中文关键词"
          - "English keyword 2"
          - "中文关键词"
        known_sources: []
        discovered_sources: []
  - name: "领域名称2"
    priority: 2
    description: "..."
    topics:
      ...
```"""


class CurriculumAgent:
    """课程规划智能体"""

    def __init__(self):
        self._llm = _CurriculumLLM()
        self.registry = self._load_registry()

    def _load_registry(self) -> List[Dict]:
        """加载预置优质资源注册表"""
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("sources", [])
        except Exception as e:
            logger.warning(f"加载 curriculum_registry.yaml 失败: {e}")
            return []

    def generate(self, goal: str, depth: str = "comprehensive") -> Dict:
        """
        生成课程表。
        Args:
            goal: 学习方向，如 "LLM全栈工程师"、"计算机视觉"、"AI Agent开发"
            depth: "quick"(5-10主题) / "comprehensive"(15-25主题) / "expert"(30-50主题)
        """
        logger.info(f"[CurriculumAgent] 生成课程表: {goal} (depth={depth})")
        report_progress(8, f"课程生成：开始规划 {goal}")
        raise_if_cancel_requested()

        raw_curriculum = self._llm_generate_curriculum(goal, depth)
        if not raw_curriculum.get("domains"):
            raise RuntimeError(
                "课程表生成失败：LLM 未返回有效课程结构。"
                "请检查 API Key、base_url、模型名和供应商兼容性。"
            )

        report_progress(82, "课程生成：匹配预置学习资源")
        self._match_registry_sources(raw_curriculum)

        curriculum = {
            "goal": goal,
            "depth": depth,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "draft",
            "domains": raw_curriculum.get("domains", []),
        }

        total_topics = sum(len(d.get("topics", [])) for d in curriculum["domains"])
        total_sources = sum(
            len(t.get("known_sources", []))
            for d in curriculum["domains"]
            for t in d.get("topics", [])
        )
        logger.info(
            f"[CurriculumAgent] 课程表生成完成: "
            f"{len(curriculum['domains'])}个领域, {total_topics}个主题, "
            f"{total_sources}个预置源匹配"
        )

        report_progress(92, "课程生成：写入 curriculum.yaml")
        self.save(curriculum)
        report_progress(96, "课程生成：课程表已生成，等待审核")
        return curriculum

    def save(self, curriculum: Dict, path: str = None):
        """保存课程表到 YAML"""
        path = path or CURRICULUM_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(curriculum, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"[CurriculumAgent] 课程表已保存: {path}")

    def load(self, path: str = None) -> Optional[Dict]:
        """加载课程表"""
        path = path or CURRICULUM_PATH
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def approve(self, path: str = None):
        """将课程表状态从 draft 改为 approved"""
        curriculum = self.load(path)
        if not curriculum:
            logger.error("未找到课程表")
            return
        curriculum["status"] = "approved"
        curriculum["approved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save(curriculum, path)
        logger.info("[CurriculumAgent] 课程表已批准")

    def update_topic_status(self, domain_name: str, topic_name: str, status: str, path: str = None):
        """更新某个主题的学习状态"""
        curriculum = self.load(path)
        if not curriculum:
            return
        for domain in curriculum.get("domains", []):
            if domain.get("name") == domain_name:
                for topic in domain.get("topics", []):
                    if topic.get("name") == topic_name:
                        topic["status"] = status
                        self.save(curriculum, path)
                        return

    def get_progress(self, path: str = None) -> Dict:
        """获取学习进度统计"""
        curriculum = self.load(path)
        if not curriculum:
            return {"total": 0, "done": 0, "studying": 0, "pending": 0}

        stats = {"total": 0, "done": 0, "studying": 0, "pending": 0}
        for domain in curriculum.get("domains", []):
            for topic in domain.get("topics", []):
                stats["total"] += 1
                state = topic.get("status", "pending")
                if state == "done":
                    stats["done"] += 1
                elif state == "studying":
                    stats["studying"] += 1
                else:
                    stats["pending"] += 1
        return stats

    def _llm_generate_curriculum(self, goal: str, depth: str) -> Dict:
        """通过带重试包装的 Worker 调用 LLM 生成课程结构"""
        try:
            output = self._llm.run(WorkerInput(metadata={"goal": goal, "depth": depth}))
            if not output.success:
                llm_cfg = self._llm.config.get("llm", {})
                raise RuntimeError(
                    "课程表生成的 LLM 调用失败。"
                    f" provider={llm_cfg.get('provider', 'openai')},"
                    f" model={self._llm.get_model()},"
                    f" base_url={llm_cfg.get('base_url', '')},"
                    f" error={output.error}"
                )
            return self._parse_curriculum_yaml(output.content)
        except Exception as e:
            logger.error(f"[CurriculumAgent] LLM生成失败: {e}")
            raise

    def _parse_curriculum_yaml(self, llm_output: str) -> Dict:
        """解析LLM输出的 YAML"""
        text = (llm_output or "").strip()
        if not text:
            raw_path = self._save_raw_llm_output(llm_output or "")
            logger.error(f"[CurriculumAgent] YAML解析失败: LLM返回空文本，原始输出已保存 {raw_path}")
            return {"domains": []}

        if "<think>" in text:
            text = re.sub(r"<think>[\s\S]*?</think>", "", text)
            if "<think>" in text:
                text = text.split("<think>")[0]
            text = text.strip()

        fenced = re.search(r"```(?:yaml|yml)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fenced:
            text = fenced.group(1).strip()
        elif "domains:" in text and not text.lstrip().startswith("domains:"):
            text = text[text.find("domains:"):].strip()

        try:
            data = yaml.safe_load(text)
            if not data or "domains" not in data:
                raise ValueError("无效的YAML结构")

            for domain in data.get("domains", []):
                domain.setdefault("priority", 99)
                for topic in domain.get("topics", []):
                    topic.setdefault("status", "pending")
                    topic.setdefault("difficulty", "intermediate")
                    topic.setdefault("search_queries", [])
                    topic.setdefault("known_sources", [])
                    topic.setdefault("discovered_sources", [])
                    topic.setdefault("description", "")

            return data
        except Exception as e:
            raw_path = self._save_raw_llm_output(llm_output or "")
            logger.error(f"[CurriculumAgent] YAML解析失败: {e}")
            logger.warning(f"[CurriculumAgent] LLM原始输出已保存 {raw_path}")
            logger.warning(f"[CurriculumAgent] LLM原始输出(前1000字符): {(llm_output or '')[:1000]}")
            return {"domains": []}

    def _save_raw_llm_output(self, llm_output: str) -> str:
        """保存课程表生成的原始输出，便于排查模型/网关兼容问题"""
        os.makedirs(CURRICULUM_DEBUG_DIR, exist_ok=True)
        path = os.path.join(
            CURRICULUM_DEBUG_DIR,
            f"curriculum_raw_{time.strftime('%Y%m%d_%H%M%S')}.txt",
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(llm_output or "")
        return path

    def _match_registry_sources(self, curriculum: Dict):
        """将预置优质源匹配到课程表中对应的主题"""
        if not self.registry:
            return

        for domain in curriculum.get("domains", []):
            for topic in domain.get("topics", []):
                topic_text = (
                    topic.get("name", "") + " " +
                    topic.get("description", "") + " " +
                    " ".join(topic.get("search_queries", []))
                ).lower()

                for source in self.registry:
                    matched = any(kw.lower() in topic_text for kw in source.get("keywords", []))
                    if not matched:
                        continue

                    existing_urls = {s.get("url") for s in topic.get("known_sources", [])}
                    if source["url"] in existing_urls:
                        continue

                    topic["known_sources"].append({
                        "name": source["name"],
                        "url": source["url"],
                        "type": source.get("type", "doc"),
                    })


class _CurriculumLLM(BaseWorker):
    """内部 LLM 调用辅助，复用 BaseWorker 的重试与配置能力"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="CurriculumLLM",
            model_level="deep",
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        goal = input_data.metadata.get("goal", "").strip()
        depth = input_data.metadata.get("depth", "comprehensive")
        if not goal:
            raise ValueError("缺少课程表生成目标(goal)")

        if depth == "quick":
            try:
                report_progress(15, "课程生成：尝试单次生成 quick 课程表")
                return self._generate_curriculum_single_shot(goal, depth)
            except Exception as e:
                logger.warning(
                    f"[CurriculumLLM] 单次生成课程表失败，切换到拆分模式 "
                    f"(goal={goal}, depth={depth}): {e}"
                )

        return self._generate_curriculum_split(goal, depth)

    def _generate_curriculum_single_shot(self, goal: str, depth: str) -> WorkerOutput:
        prompt = _build_curriculum_prompt(goal, depth)
        errors = []

        for max_tokens in (6000, 4500):
            raise_if_cancel_requested()
            try:
                result = self.llm_call(
                    prompt,
                    system=CURRICULUM_SYSTEM_PROMPT,
                    enable_thinking=False,
                    max_tokens=max_tokens,
                )
                return WorkerOutput(
                    success=True,
                    content=result,
                    data={"goal": goal, "depth": depth, "mode": "single_shot", "max_tokens": max_tokens},
                )
            except Exception as e:
                errors.append(f"max_tokens={max_tokens}: {e}")
                logger.warning(
                    f"[CurriculumLLM] 调用失败，尝试降级参数重试 "
                    f"(goal={goal}, depth={depth}, max_tokens={max_tokens}): {e}"
                )

        raise RuntimeError(" | ".join(errors))

    def _generate_curriculum_split(self, goal: str, depth: str) -> WorkerOutput:
        settings = self._depth_settings(depth)
        report_progress(15, "课程生成：规划领域骨架")
        domain_specs = self._generate_domain_plan(goal, depth, settings)
        if not domain_specs:
            raise RuntimeError("拆分生成课程表失败：未生成任何领域骨架")

        assembled_domains = []
        total_domains = len(domain_specs)
        for index, domain in enumerate(domain_specs, start=1):
            raise_if_cancel_requested()
            progress = 25 + int((index - 1) / max(total_domains, 1) * 50)
            report_progress(
                progress,
                f"课程生成：生成主题 {index}/{total_domains} - {domain.get('name', '未命名领域')}",
            )
            topics = self._generate_domain_topics(goal, depth, domain, domain_specs, settings)
            assembled_domains.append({
                "name": domain.get("name", "未命名领域"),
                "priority": domain.get("priority", 99),
                "description": domain.get("description", ""),
                "topics": topics,
            })

        report_progress(78, "课程生成：组装课程表 YAML")
        curriculum = {"domains": assembled_domains}
        return WorkerOutput(
            success=True,
            content=yaml.dump(curriculum, allow_unicode=True, default_flow_style=False, sort_keys=False),
            data={
                "goal": goal,
                "depth": depth,
                "mode": "split",
                "domains": len(assembled_domains),
                "topics": sum(len(domain.get("topics", [])) for domain in assembled_domains),
            },
        )

    def _generate_domain_plan(self, goal: str, depth: str, settings: Dict[str, int]) -> List[Dict]:
        prompt = f"""请先只规划学习方向的“领域骨架”，不要一次生成完整课程表。
学习方向: {goal}
深度: {depth}

要求：
1. 只输出 {settings['min_domains']}-{settings['max_domains']} 个学习领域
2. 每个领域给出 priority、description、topic_count
3. 所有领域的 topic_count 总数大致落在 {settings['min_topics']}-{settings['max_topics']} 之间
4. 领域之间不要重复，覆盖理论、实践、工程、前沿

请严格按 YAML 输出：
```yaml
domains:
  - name: "领域名称"
    priority: 1
    description: "这个领域为什么重要"
    topic_count: 4
```"""

        result = self.llm_call(
            prompt,
            system=CURRICULUM_SYSTEM_PROMPT,
            enable_thinking=False,
            max_tokens=2200,
        )
        data = yaml.safe_load(self._extract_yaml_block(result, "domains:")) or {}
        domains = data.get("domains", [])

        cleaned = []
        for domain in domains:
            cleaned.append({
                "name": domain.get("name", "未命名领域"),
                "priority": domain.get("priority", 99),
                "description": domain.get("description", ""),
                "topic_count": max(1, int(domain.get("topic_count", settings["default_topic_count"]))),
            })
        return cleaned

    def _generate_domain_topics(
        self,
        goal: str,
        depth: str,
        domain: Dict,
        all_domains: List[Dict],
        settings: Dict[str, int],
    ) -> List[Dict]:
        topic_count = max(1, int(domain.get("topic_count", settings["default_topic_count"])))
        batch_size = settings["topic_batch_size"]
        generated_topics = []

        domain_outline = "\n".join(
            f"- P{item.get('priority', 99)} {item.get('name', '')}: {item.get('description', '')}"
            for item in all_domains
        )

        for start in range(0, topic_count, batch_size):
            raise_if_cancel_requested()
            current_batch_size = min(batch_size, topic_count - start)
            existing_names = [topic.get("name", "") for topic in generated_topics]
            report_progress(
                None,
                f"课程生成：{domain.get('name', '未命名领域')} topic {start + 1}-{start + current_batch_size}/{topic_count}",
            )

            prompt = f"""你现在只负责为单个领域生成一小批 topic，避免长输出被截断。
学习方向: {goal}
深度: {depth}

全局领域骨架:
{domain_outline}

当前领域:
- name: {domain.get('name', '')}
- priority: {domain.get('priority', 99)}
- description: {domain.get('description', '')}

当前批次任务:
1. 生成这个领域的第 {start + 1} 到 {start + current_batch_size} 个 topic
2. 本批次只输出 {current_batch_size} 个 topic
3. 不要与已生成 topic 重复
4. 每个 topic 必须包含中英双语 search_queries

已生成 topic:
{existing_names if existing_names else ['(无)']}

请严格按 YAML 输出：
```yaml
topics:
  - name: "主题名称"
    status: pending
    difficulty: beginner
    description: "一句话说明"
    search_queries:
      - "English keyword"
      - "中文关键词"
      - "English keyword 2"
      - "中文关键词 2"
    known_sources: []
    discovered_sources: []
```"""

            result = self.llm_call(
                prompt,
                system=CURRICULUM_SYSTEM_PROMPT,
                enable_thinking=False,
                max_tokens=2200,
            )
            parsed = yaml.safe_load(self._extract_yaml_block(result, "topics:")) or {}
            batch_topics = parsed.get("topics", [])
            for topic in batch_topics:
                normalized = self._normalize_topic(topic)
                if normalized["name"] and normalized["name"] not in existing_names:
                    generated_topics.append(normalized)
                    existing_names.append(normalized["name"])

        return generated_topics[:topic_count]

    @staticmethod
    def _depth_settings(depth: str) -> Dict[str, int]:
        if depth == "quick":
            return {
                "min_domains": 3,
                "max_domains": 4,
                "min_topics": 5,
                "max_topics": 10,
                "default_topic_count": 2,
                "topic_batch_size": 3,
            }
        if depth == "expert":
            return {
                "min_domains": 5,
                "max_domains": 8,
                "min_topics": 30,
                "max_topics": 50,
                "default_topic_count": 6,
                "topic_batch_size": 4,
            }
        return {
            "min_domains": 4,
            "max_domains": 6,
            "min_topics": 15,
            "max_topics": 25,
            "default_topic_count": 4,
            "topic_batch_size": 4,
        }

    @staticmethod
    def _normalize_topic(topic: Dict) -> Dict:
        return {
            "name": topic.get("name", "").strip(),
            "status": topic.get("status", "pending"),
            "difficulty": topic.get("difficulty", "intermediate"),
            "description": topic.get("description", ""),
            "search_queries": topic.get("search_queries", []) or [],
            "known_sources": topic.get("known_sources", []) or [],
            "discovered_sources": topic.get("discovered_sources", []) or [],
        }

    @staticmethod
    def _extract_yaml_block(content: str, anchor: str) -> str:
        text = content or ""
        if "<think>" in text:
            text = re.sub(r"<think>[\s\S]*?</think>", "", text)
            if "<think>" in text:
                text = text.split("<think>")[0]
        fenced = re.search(r"```(?:yaml|yml)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        if anchor in text and not text.lstrip().startswith(anchor):
            return text[text.find(anchor):].strip()
        return text.strip()
