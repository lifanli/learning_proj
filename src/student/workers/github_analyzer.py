"""
GitHub深度分析Worker (GitHubAnalyzer)
======================================
对GitHub仓库进行深度读取和分析。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import Material
from src.tools.github_api import GitHubAPI
from src.utils.logger import logger


class GitHubAnalyzer(BaseWorker):
    """GitHub仓库深度分析Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="GitHubAnalyzer",
            description="深度分析GitHub仓库：README+源码+架构",
            model_level="deep",
            max_retries=2,
            timeout=120,
        ))
        self.github = GitHubAPI()

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        url = input_data.url
        if not url:
            return WorkerOutput(success=False, error="缺少GitHub URL")

        # 深度读取仓库
        repo_data = self.github.get_repo_deep(url, max_files=15)
        if not repo_data:
            return WorkerOutput(success=False, error=f"无法访问仓库: {url}")

        # 用LLM生成结构化分析
        analysis = self._analyze_repo(repo_data)

        # 构建完整内容（不截断）
        full_content = self._build_full_content(repo_data, analysis)

        material = Material(
            source_url=url,
            source_type="github",
            title=f"GitHub: {repo_data.get('name', '')}",
            content=full_content,
            summary=analysis.get("summary", ""),
            tags=repo_data.get("topics", []),
            code_blocks=[
                {"language": repo_data.get("language", ""), "code": kf["content"][:2000], "comment": kf["path"]}
                for kf in repo_data.get("key_files", [])
                if kf.get("content")
            ],
            metadata={
                "stars": repo_data.get("stars", 0),
                "language": repo_data.get("language", ""),
                "structure": repo_data.get("structure", [])[:100],
            }
        )

        return WorkerOutput(
            success=True,
            content=full_content,
            data={"repo": repo_data, "analysis": analysis},
            materials=[material],
        )

    def _analyze_repo(self, repo_data: dict) -> dict:
        """用LLM分析仓库"""
        # 准备输入
        readme_excerpt = repo_data.get("readme", "")[:3000]
        key_files_text = ""
        for kf in repo_data.get("key_files", [])[:5]:
            key_files_text += f"\n--- {kf['path']} ---\n{kf['content'][:1500]}\n"

        structure_text = "\n".join(repo_data.get("structure", [])[:50])

        prompt = f"""分析以下GitHub仓库，提供结构化分析报告。

仓库名: {repo_data.get('name', '')}
描述: {repo_data.get('description', '')}
Stars: {repo_data.get('stars', 0)}
语言: {repo_data.get('language', '')}
标签: {', '.join(repo_data.get('topics', []))}

README (节选):
{readme_excerpt}

目录结构:
{structure_text}

关键源码:
{key_files_text}

请用中文提供：
1. 一句话总结（summary）
2. 项目解决什么问题
3. 核心架构/设计模式
4. 关键技术栈
5. 适合的读者/使用场景"""

        try:
            result = self.llm_call(
                prompt,
                system="你是一个资深软件工程师，擅长分析开源项目。请提供深入但简洁的技术分析。",
                enable_thinking=True,
            )
            return {"summary": result[:200], "analysis": result}
        except Exception as e:
            logger.warning(f"仓库分析失败: {e}")
            return {"summary": repo_data.get("description", ""), "analysis": ""}

    def _build_full_content(self, repo_data: dict, analysis: dict) -> str:
        """构建完整的仓库内容文本"""
        parts = []
        parts.append(f"# {repo_data.get('name', 'Unknown')}")
        parts.append(f"\n> {repo_data.get('description', '')}")
        parts.append(f"\n⭐ Stars: {repo_data.get('stars', 0)} | 语言: {repo_data.get('language', '')}")
        if repo_data.get("topics"):
            parts.append(f"标签: {', '.join(repo_data['topics'])}")

        if analysis.get("analysis"):
            parts.append(f"\n## 分析报告\n{analysis['analysis']}")

        if repo_data.get("readme"):
            parts.append(f"\n## README\n{repo_data['readme']}")

        if repo_data.get("key_files"):
            parts.append("\n## 关键源码")
            for kf in repo_data["key_files"]:
                parts.append(f"\n### {kf['path']}\n```\n{kf['content']}\n```")

        return "\n".join(parts)
