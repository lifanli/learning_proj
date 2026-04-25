import os
import yaml
from src.agents.base_agent import BaseAgent
from src.utils.logger import logger


class StructurePlanner(BaseAgent):
    """动态目录规划器：基于 LLM 决定内容分类，可动态创建新分类"""

    TOC_PATH = "config/toc.yaml"

    def __init__(self):
        super().__init__(
            role_name="目录规划师",
            role_instruction=(
                "你是知识库的目录规划师。你的任务是根据内容摘要，将其归入最合适的分类目录。\n"
                "如果现有分类都不合适，你可以建议创建新分类。\n"
                "回复格式严格遵循要求，不要添加多余内容。"
            )
        )
        self.kb_root = "knowledge_base"

    def _load_toc(self) -> dict:
        """加载目录配置"""
        try:
            with open(self.TOC_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"categories": [], "next_category_index": 0}
        except FileNotFoundError:
            logger.warning("未找到目录配置文件，创建默认配置")
            default = {"categories": [], "next_category_index": 0}
            self._save_toc(default)
            return default

    def _save_toc(self, toc: dict):
        """保存目录配置"""
        with open(self.TOC_PATH, "w", encoding="utf-8") as f:
            yaml.dump(toc, f, allow_unicode=True, default_flow_style=False)

    def plan(self, topic: str, content_summary: str) -> str:
        """
        根据主题和内容摘要，决定内容应归入哪个分类目录。
        返回目标目录名（如 '01_AI理论与算法'）。
        如果需要创建新分类，会自动创建。
        """
        toc = self._load_toc()
        categories = toc.get("categories", [])

        # 构建分类列表描述
        cat_descriptions = "\n".join(
            f"- {c['dir_name']}: {c['description']}"
            for c in categories
        )

        prompt = f"""根据以下内容信息，决定它应该归入哪个分类目录。

主题: {topic}
内容摘要: {content_summary[:500]}

现有分类:
{cat_descriptions}

请严格按以下格式回复（只回复一行）:
- 如果匹配现有分类: EXISTING|目录名
- 如果需要新分类: NEW|分类名称|分类描述

示例:
EXISTING|01_AI理论与算法
NEW|03_智能体系统|AI Agent 框架、多智能体协作、自主系统等
"""

        result = self.chat(prompt, stream=False).strip()
        logger.info(f"目录规划结果: {result}")

        return self._parse_plan_result(result, toc)

    def _parse_plan_result(self, result: str, toc: dict) -> str:
        """解析 LLM 的分类决策结果"""
        lines = result.strip().split("\n")
        # 取第一行有效内容
        decision = ""
        for line in lines:
            line = line.strip()
            if line.startswith("EXISTING|") or line.startswith("NEW|"):
                decision = line
                break

        if not decision:
            # 尝试模糊匹配现有分类（去除空格后匹配）
            categories = toc.get("categories", [])
            result_nospace = result.replace(" ", "")
            for cat in categories:
                if cat["dir_name"].replace(" ", "") in result_nospace or cat["name"].replace(" ", "") in result_nospace:
                    logger.info(f"模糊匹配到分类: {cat['dir_name']}")
                    return cat["dir_name"]
            # 默认归入第一个分类
            if categories:
                fallback = categories[0]["dir_name"]
                logger.warning(f"无法解析分类决策，使用默认分类: {fallback}")
                return fallback
            return "00_每日资讯"

        parts = decision.split("|")

        if parts[0] == "EXISTING" and len(parts) >= 2:
            dir_name = parts[1].strip()
            # 验证分类存在
            valid_dirs = [c["dir_name"] for c in toc.get("categories", [])]
            if dir_name in valid_dirs:
                return dir_name
            # 去除空格后精确匹配
            dir_name_nospace = dir_name.replace(" ", "")
            for vd in valid_dirs:
                if dir_name_nospace == vd.replace(" ", ""):
                    logger.info(f"空格归一化匹配到分类: {vd}")
                    return vd
            # 模糊匹配：包含关系
            for vd in valid_dirs:
                vd_nospace = vd.replace(" ", "")
                if dir_name_nospace in vd_nospace or vd_nospace in dir_name_nospace:
                    logger.info(f"模糊匹配到分类: {vd}")
                    return vd
            logger.warning(f"分类 {dir_name} 不存在，使用默认分类")
            return toc["categories"][0]["dir_name"] if toc["categories"] else "00_每日资讯"

        elif parts[0] == "NEW" and len(parts) >= 3:
            name = parts[1].strip()
            description = parts[2].strip()
            return self._create_new_category(toc, name, description)

        logger.warning(f"无法解析分类决策: {result}")
        return toc["categories"][0]["dir_name"] if toc.get("categories") else "00_每日资讯"

    def _create_new_category(self, toc: dict, name: str, description: str) -> str:
        """创建新分类目录"""
        import re
        idx = toc.get("next_category_index", len(toc.get("categories", [])))
        # 移除 LLM 可能返回的数字前缀（如 "03_智能体系统" → "智能体系统"）
        clean_name = re.sub(r'^\d+[_\s]*', '', name).strip()
        if not clean_name:
            clean_name = name
        dir_name = f"{idx:02d}_{clean_name}"

        # 创建文件系统目录
        dir_path = os.path.join(self.kb_root, dir_name)
        os.makedirs(dir_path, exist_ok=True)

        # 更新 toc.yaml
        new_category = {
            "index": f"{idx:02d}",
            "name": name,
            "description": description,
            "dir_name": dir_name
        }
        toc["categories"].append(new_category)
        toc["next_category_index"] = idx + 1
        self._save_toc(toc)

        logger.info(f"已创建新分类: {dir_name} - {description}")
        return dir_name
