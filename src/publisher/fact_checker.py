import re
import requests
from src.agents.base_agent import BaseAgent
from src.utils.logger import logger


class FactChecker(BaseAgent):
    """事实核查智能体：验证 ArXiv ID、RAG 交叉验证、来源归属检查"""

    def __init__(self):
        super().__init__(
            role_name="事实核查员",
            role_instruction=(
                "你是一名严谨的事实核查员。你的任务是检查内容的准确性，包括：\n"
                "1. 验证引用的论文和来源是否真实\n"
                "2. 检查技术描述是否准确\n"
                "3. 确认关键声明有可追溯的来源\n"
                "如果发现问题，请明确指出并建议修正。"
            )
        )

    def check(self, content: str, source: str, rag_context: str = "") -> dict:
        """
        执行事实核查流水线。
        返回 dict: {passed: bool, issues: list[str], corrected_content: str}
        """
        issues = []

        # 1. 检查 ArXiv ID 真实性
        arxiv_issues = self._verify_arxiv_ids(content)
        issues.extend(arxiv_issues)

        # 2. RAG 交叉验证
        if rag_context:
            rag_issues = self._cross_validate_with_rag(content, rag_context)
            issues.extend(rag_issues)

        # 3. LLM 来源归属检查
        attribution_issues = self._check_source_attribution(content, source)
        issues.extend(attribution_issues)

        passed = len(issues) == 0
        corrected_content = content

        if not passed:
            logger.warning(f"事实核查发现 {len(issues)} 个问题")
            corrected_content = self._attempt_correction(content, issues)
        else:
            logger.info("事实核查通过")

        return {
            "passed": passed,
            "issues": issues,
            "corrected_content": corrected_content
        }

    def _verify_arxiv_ids(self, content: str) -> list:
        """验证内容中引用的 ArXiv ID 是否真实存在"""
        issues = []
        # 匹配 ArXiv ID 格式: YYMM.NNNNN 或 category/YYMMNNN
        arxiv_patterns = [
            r'\b(\d{4}\.\d{4,5})\b',
            r'arxiv[:/](\d{4}\.\d{4,5})',
        ]

        arxiv_ids = set()
        for pattern in arxiv_patterns:
            arxiv_ids.update(re.findall(pattern, content, re.IGNORECASE))

        for arxiv_id in arxiv_ids:
            if not self._check_arxiv_exists(arxiv_id):
                issues.append(f"ArXiv ID {arxiv_id} 验证失败：可能不存在或无法访问")

        if arxiv_ids:
            logger.info(f"验证了 {len(arxiv_ids)} 个 ArXiv ID，{len(issues)} 个存在问题")

        return issues

    def _check_arxiv_exists(self, arxiv_id: str) -> bool:
        """通过 ArXiv API 检查论文是否存在"""
        try:
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 检查返回的 XML 中是否包含有效结果
                return "<entry>" in response.text and "<title>" in response.text
            return False
        except Exception as e:
            logger.warning(f"ArXiv API 请求失败 ({arxiv_id}): {e}")
            return True  # 网络问题时默认信任

    def _cross_validate_with_rag(self, content: str, rag_context: str) -> list:
        """使用 RAG 上下文交叉验证内容"""
        issues = []

        prompt = f"""请对比以下两段内容，检查"待核查内容"中是否有与"参考上下文"矛盾的事实性错误。

参考上下文（来自知识库）:
{rag_context[:2000]}

待核查内容:
{content[:2000]}

如果没有发现矛盾，回复: 无矛盾
如果发现矛盾，逐条列出，每行一个，格式为: 矛盾|具体描述"""

        result = self.chat(prompt, stream=False)
        if result and "无矛盾" not in result:
            for line in result.strip().split("\n"):
                line = line.strip()
                if line.startswith("矛盾|"):
                    issues.append(f"RAG 交叉验证: {line[3:]}")
                elif line and "矛盾" not in line.lower() and len(line) > 5:
                    issues.append(f"RAG 交叉验证: {line}")

        return issues

    def _check_source_attribution(self, content: str, source: str) -> list:
        """检查内容是否有适当的来源归属"""
        issues = []

        prompt = f"""检查以下内容的来源归属是否充分。内容声称来自: {source}

内容:
{content[:2000]}

检查要点:
1. 关键技术声明是否有来源支撑
2. 数据和数字是否标注了出处
3. 是否存在没有根据的夸大表述

如果归属充分，回复: 归属充分
如果有问题，逐条列出，每行一个，格式为: 归属问题|具体描述"""

        result = self.chat(prompt, stream=False)
        if result and "归属充分" not in result:
            for line in result.strip().split("\n"):
                line = line.strip()
                if line.startswith("归属问题|"):
                    issues.append(f"来源归属: {line[5:]}")

        return issues

    def _attempt_correction(self, content: str, issues: list) -> str:
        """尝试根据发现的问题修正内容"""
        issues_text = "\n".join(f"- {issue}" for issue in issues)

        prompt = f"""以下内容存在一些事实核查问题，请修正内容。
对于无法验证的声明，添加"[待验证]"标注。
对于虚假的 ArXiv ID，移除或标注为"[ID待确认]"。

发现的问题:
{issues_text}

原始内容:
{content[:3000]}

请输出修正后的完整内容:"""

        result = self.chat(prompt, stream=False)
        if result and not result.startswith("Error:"):
            return result
        return content
