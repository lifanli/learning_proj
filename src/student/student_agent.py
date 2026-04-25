"""
学生智能体 (StudentAgent)
==========================
主控：接收学习任务，分解为Worker任务DAG，调度执行，将素材存入MaterialStore。

支持的学习模式：
- study_course: 课程学习（批量页面抓取 → 翻译 → 标注）
- study_wechat: 微信文章学习（抓取 → 图片解读 → 引用追踪）
- study_github: GitHub仓库学习（深度分析源码）
- study_arxiv: ArXiv论文学习（PDF下载 → 结构化分析）
- study_topic: 按主题自动搜索资源并学习
- study_curriculum: 按课程表自动执行全部学习任务
"""

import asyncio
import uuid
import yaml
from typing import List, Dict, Optional

from src.core.progress import TaskCancellationRequested, raise_if_cancel_requested, report_progress
from src.core.material_store import MaterialStore, Material
from src.core.worker import WorkerInput, WorkerOutput
from src.core.task_engine import TaskEngine, TaskNode, TaskDAG, TaskStatus
from src.student.study_planner import StudyPlanner, StudyPlan
from src.student.material_pipeline import MaterialProcessingPipeline
from src.student.workers.content_fetcher import ContentFetcher
from src.student.workers.image_worker import ImageWorker
from src.student.workers.code_extractor import CodeExtractor
from src.student.workers.term_extractor import TermExtractor
from src.student.workers.reference_tracker import ReferenceTracker
from src.student.workers.github_analyzer import GitHubAnalyzer
from src.student.workers.paper_analyzer import PaperAnalyzer
from src.student.workers.translator_worker import TranslatorWorker
from src.student.workers.topic_tagger import TopicTagger
from src.student.workers.gap_detector import GapDetector
from src.utils.logger import logger


class StudentAgent:
    """学生智能体 - 主控"""

    def __init__(self):
        self.config = self._load_config()
        self.store = MaterialStore(self.config.get("paths", {}).get("materials", "data/materials"))
        self.planner = StudyPlanner()
        self.engine = TaskEngine(
            max_parallel=self.config.get("student", {}).get("max_concurrent_fetches", 10)
        )

        # Workers
        self.fetcher = ContentFetcher()
        self.image_worker = ImageWorker()
        self.code_extractor = CodeExtractor()
        self.term_extractor = TermExtractor()
        self.ref_tracker = ReferenceTracker()
        self.github_analyzer = GitHubAnalyzer()
        self.paper_analyzer = PaperAnalyzer()
        self.translator = TranslatorWorker()
        self.tagger = TopicTagger()
        self.gap_detector = GapDetector()

    def _load_config(self) -> dict:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    async def study_course(self, url: str, max_pages: int = 50) -> Dict:
        """
        学习在线课程。
        1. 制定学习计划（发现所有章节）
        2. 并行抓取每个章节页面（受 max_concurrent_fetches 限制）
        3. 每页独立执行 enrich DAG（图片/代码/术语/引用并行 → 翻译 → 标签）
        4. 全部存入素材库
        """
        logger.info(f"[StudentAgent] 开始学习课程: {url}")

        # 1. 学习计划
        plan = self.planner.plan_course(url, max_pages)
        if not plan.pages:
            return {"error": "未发现课程页面", "materials": []}

        # 创建父素材（课程根）
        course_material = Material(
            source_url=url,
            source_type="course",
            title=plan.title,
            content=f"课程: {plan.title}\nURL: {url}\n共 {len(plan.pages)} 个章节",
            metadata={"total_pages": len(plan.pages)},
        )
        parent_id = self.store.save(course_material)

        # 2. 并行处理页面（受 semaphore 限制）
        max_concurrent = self.config.get("student", {}).get("max_concurrent_fetches", 10)
        sem = asyncio.Semaphore(max_concurrent)

        async def process_page(page):
            async with sem:
                return await self._process_course_page(page, parent_id)

        tasks = [process_page(page) for page in plan.pages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        material_ids = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"页面处理异常: {plan.pages[i]['url']} - {result}")
            elif result:
                material_ids.append(result)
            # Log progress
            logger.info(
                f"[StudentAgent] 页面进度 {i+1}/{len(plan.pages)}"
            )

        # 追踪GitHub/ArXiv引用
        if self.config.get("student", {}).get("follow_references", True):
            await self._follow_references(plan, parent_id, material_ids)

        logger.info(f"[StudentAgent] 课程学习完成: {plan.title} | 素材数={len(material_ids)}")
        return {
            "title": plan.title,
            "parent_id": parent_id,
            "material_ids": material_ids,
            "total_pages": len(plan.pages),
        }

    async def _process_course_page(self, page: dict, parent_id: str) -> Optional[str]:
        """处理单个课程页面：抓取 → enrich DAG → 保存"""
        page_url = page["url"]

        # 去重检查
        existing = self.store.exists_by_url(page_url)
        if existing:
            logger.info(f"页面已存在，跳过: {page_url}")
            return existing

        # 抓取页面（sync worker → thread pool）
        loop = asyncio.get_event_loop()
        fetch_input = WorkerInput(
            url=page_url,
            parent_id=parent_id,
            metadata={"source_type": "course_page", "order": page["order"]},
        )
        fetch_output = await loop.run_in_executor(None, self.fetcher.run, fetch_input)
        if not fetch_output.success:
            logger.warning(f"抓取失败: {page_url} - {fetch_output.error}")
            return None

        if not fetch_output.materials:
            return None

        mat = fetch_output.materials[0]
        mat.parent_id = parent_id
        mat.order_index = page["order"]
        mat.source_type = "course_page"
        if not mat.id:
            mat.id = uuid.uuid4().hex[:12]

        # Enrich via DAG（image/code/term/ref 并行 → translator → tagger）
        mat = await self._enrich_material(mat, fetch_output)

        # 保存
        mid = self.store.save(mat)
        logger.info(f"[StudentAgent] 页面完成: {mat.title[:50]}")
        return mid

    async def study_wechat(self, url: str) -> Dict:
        """学习微信文章"""
        logger.info(f"[StudentAgent] 开始学习微信文章: {url}")

        plan = self.planner.plan_wechat(url)

        # 抓取文章
        fetch_input = WorkerInput(
            url=url,
            metadata={"source_type": "wechat"},
        )
        fetch_output = self.fetcher.run(fetch_input)
        if not fetch_output.success:
            return {"error": fetch_output.error}

        mat = fetch_output.materials[0] if fetch_output.materials else Material(
            source_url=url, source_type="wechat", title=plan.title, content=fetch_output.content
        )
        mat.source_type = "wechat"

        # 处理流水线：图片 → 代码 → 术语 → 引用 → 翻译 → 标签（DAG并行）
        mat = await self._enrich_material(mat, fetch_output)

        # 保存
        mat_id = self.store.save(mat)

        # 追踪引用
        ref_materials = []
        if self.config.get("student", {}).get("follow_references", True):
            for gh_url in plan.github_urls:
                gh_output = self.github_analyzer.run(WorkerInput(url=gh_url))
                if gh_output.success and gh_output.materials:
                    for ref_mat in gh_output.materials:
                        ref_mat.parent_id = mat_id
                        rid = self.store.save(ref_mat)
                        ref_materials.append(rid)

            for ax_url in plan.arxiv_urls:
                ax_output = self.paper_analyzer.run(WorkerInput(url=ax_url))
                if ax_output.success and ax_output.materials:
                    for ref_mat in ax_output.materials:
                        ref_mat.parent_id = mat_id
                        rid = self.store.save(ref_mat)
                        ref_materials.append(rid)

        logger.info(f"[StudentAgent] 微信文章学习完成: {mat.title} | 引用追踪={len(ref_materials)}")
        return {
            "title": mat.title,
            "material_id": mat_id,
            "ref_materials": ref_materials,
        }

    async def study_github(self, url: str) -> Dict:
        """学习GitHub仓库"""
        logger.info(f"[StudentAgent] 开始学习GitHub仓库: {url}")

        output = self.github_analyzer.run(WorkerInput(url=url))
        if not output.success:
            return {"error": output.error}

        mat = output.materials[0] if output.materials else Material(
            source_url=url, source_type="github", content=output.content
        )

        # 标签
        tag_output = self.tagger.run(WorkerInput(
            content=mat.content,
            metadata={"title": mat.title},
        ))
        if tag_output.success:
            mat.tags = tag_output.data.get("tags", [])

        mat_id = self.store.save(mat)
        logger.info(f"[StudentAgent] GitHub仓库学习完成: {mat.title}")
        return {"title": mat.title, "material_id": mat_id}

    async def study_arxiv(self, url: str) -> Dict:
        """学习ArXiv论文"""
        logger.info(f"[StudentAgent] 开始学习ArXiv论文: {url}")

        output = self.paper_analyzer.run(WorkerInput(url=url))
        if not output.success:
            return {"error": output.error}

        mat = output.materials[0] if output.materials else Material(
            source_url=url, source_type="arxiv", content=output.content
        )

        # 翻译
        trans_output = self.translator.run(WorkerInput(content=mat.content))
        if trans_output.success and trans_output.data.get("translated"):
            mat.content = trans_output.content
            mat.language = "zh"

        # 标签
        tag_output = self.tagger.run(WorkerInput(
            content=mat.content,
            metadata={"title": mat.title},
        ))
        if tag_output.success:
            mat.tags = tag_output.data.get("tags", [])

        mat_id = self.store.save(mat)
        logger.info(f"[StudentAgent] ArXiv论文学习完成: {mat.title}")
        return {"title": mat.title, "material_id": mat_id}

    async def _enrich_material(self, mat: Material, fetch_output: WorkerOutput) -> Material:
        """
        为素材添加图片、代码、术语、引用、翻译、标签，并补充质量元数据。
        """
        if not mat.id:
            mat.id = uuid.uuid4().hex[:12]

        pipeline = MaterialProcessingPipeline(
            workers={
                "image": self.image_worker,
                "code": self.code_extractor,
                "term": self.term_extractor,
                "ref": self.ref_tracker,
                "translator": self.translator,
                "tagger": self.tagger,
            },
            config=self.config,
            image_save_dir=self.store.get_image_path(mat.id),
        )
        dag = pipeline.build_enrich_dag(mat, fetch_output)
        dag = await self.engine.execute(dag)
        return pipeline.apply_results(mat, dag)

    def _build_enrich_dag(self, mat: Material, fetch_output: WorkerOutput) -> TaskDAG:
        """兼容旧调用：委托给 MaterialProcessingPipeline 构建素材加工 DAG。"""
        pipeline = MaterialProcessingPipeline(
            workers={
                "image": self.image_worker,
                "code": self.code_extractor,
                "term": self.term_extractor,
                "ref": self.ref_tracker,
                "translator": self.translator,
                "tagger": self.tagger,
            },
            config=self.config,
            image_save_dir=self.store.get_image_path(mat.id),
        )
        return pipeline.build_enrich_dag(mat, fetch_output)

    def _apply_enrich_results(self, mat: Material, dag: TaskDAG) -> Material:
        """兼容旧调用：委托给 MaterialProcessingPipeline 应用加工结果。"""
        pipeline = MaterialProcessingPipeline(
            workers={
                "image": self.image_worker,
                "code": self.code_extractor,
                "term": self.term_extractor,
                "ref": self.ref_tracker,
                "translator": self.translator,
                "tagger": self.tagger,
            },
            config=self.config,
            image_save_dir=self.store.get_image_path(mat.id),
        )
        return pipeline.apply_results(mat, dag)

    async def _follow_references(self, plan: StudyPlan, parent_id: str, material_ids: list):
        """追踪引用链接（GitHub/ArXiv）"""
        # 从所有已收集素材中聚合引用
        all_refs = set()
        for mid in material_ids:
            mat = self.store.get(mid)
            if mat and isinstance(mat.references, list):
                for ref in mat.references:
                    if isinstance(ref, dict):
                        all_refs.add((ref.get("url", ""), ref.get("type", "")))

        # 也包含计划中发现的链接
        for gh_url in plan.github_urls:
            all_refs.add((gh_url, "github"))
        for ax_url in plan.arxiv_urls:
            all_refs.add((ax_url, "arxiv"))

        for ref_url, ref_type in all_refs:
            if not ref_url:
                continue

            # 去重检查
            if self.store.exists_by_url(ref_url):
                continue

            try:
                if ref_type == "github":
                    output = self.github_analyzer.run(WorkerInput(url=ref_url))
                elif ref_type == "arxiv":
                    output = self.paper_analyzer.run(WorkerInput(url=ref_url))
                else:
                    continue

                if output.success and output.materials:
                    for ref_mat in output.materials:
                        ref_mat.parent_id = parent_id
                        self.store.save(ref_mat)
                        logger.info(f"[StudentAgent] 引用追踪完成: {ref_url}")

            except Exception as e:
                logger.warning(f"[StudentAgent] 引用追踪失败 {ref_url}: {e}")

    # ==================== 主动学习模式 ====================

    async def study_topic(self, topic: str, search_queries: List[str] = None,
                          max_resources: int = 8) -> Dict:
        """
        按主题自动搜索资源并学习。

        TopicExplorer 搜索多渠道资源 → 按类型分派到对应 study_* 方法。
        """
        from src.student.topic_explorer import TopicExplorer

        logger.info(f"[StudentAgent] 开始按主题学习: {topic}")

        explorer = TopicExplorer()
        resources = explorer.explore(topic, search_queries, max_results=max_resources)

        if not resources:
            return {"error": f"未找到与 '{topic}' 相关的学习资源", "materials": []}

        logger.info(f"[StudentAgent] 发现 {len(resources)} 个资源，开始学习...")

        all_material_ids = []
        all_errors = []

        for i, res in enumerate(resources):
            url = res.get("url", "")
            res_type = res.get("type", "web")
            title = res.get("title", url)

            logger.info(
                f"[StudentAgent] 资源 {i+1}/{len(resources)}: "
                f"[{res_type}] {title[:60]}"
            )

            # 去重
            if self.store.exists_by_url(url):
                logger.info(f"  已存在，跳过: {url}")
                continue

            try:
                if res_type == "github":
                    result = await self.study_github(url)
                elif res_type == "arxiv":
                    result = await self.study_arxiv(url)
                elif res_type == "course":
                    result = await self.study_course(url, max_pages=30)
                else:
                    # doc / web → 当做普通网页抓取
                    result = await self._study_web_page(url)

                if "error" in result:
                    all_errors.append(f"[{res_type}] {url}: {result['error']}")
                else:
                    if "material_ids" in result:
                        all_material_ids.extend(result["material_ids"])
                    elif "material_id" in result:
                        all_material_ids.append(result["material_id"])

            except Exception as e:
                all_errors.append(f"[{res_type}] {url}: {e}")
                logger.warning(f"[StudentAgent] 资源学习失败: {url} - {e}")

        logger.info(
            f"[StudentAgent] 主题学习完成: {topic} | "
            f"素材={len(all_material_ids)}, 失败={len(all_errors)}"
        )
        return {
            "title": topic,
            "material_ids": all_material_ids,
            "errors": all_errors,
            "resources_found": len(resources),
        }

    async def study_curriculum(self, curriculum_path: str = None) -> Dict:
        """
        按课程表自动执行全部学习任务。

        读取 approved 状态的 curriculum.yaml，按 priority 顺序遍历每个 topic，
        调用 study_topic 进行学习，更新 topic 状态。

        Returns:
            {"completed": int, "failed": int, "skipped": int, "total": int}
        """
        from src.student.curriculum_agent import CurriculumAgent

        ca = CurriculumAgent()
        curriculum = ca.load(curriculum_path)

        if not curriculum:
            return {"error": "未找到课程表，请先生成课程表"}

        runnable_statuses = {"approved", "in_progress", "completed", "completed_with_errors"}
        if curriculum.get("status") not in runnable_statuses:
            return {"error": f"课程表状态为 '{curriculum.get('status')}'，需要先审批(approved)"}

        report_progress(5, "自动学习：加载课程表")

        # 标记为执行中
        curriculum["status"] = "in_progress"
        ca.save(curriculum, curriculum_path)

        stats = {"completed": 0, "failed": 0, "skipped": 0, "total": 0}

        # 按 priority 排序领域
        domains = sorted(
            curriculum.get("domains", []),
            key=lambda d: d.get("priority", 99)
        )
        total_topics = sum(len(domain.get("topics", [])) for domain in domains)
        processed_topics = 0
        report_progress(8, f"自动学习：准备学习 {total_topics} 个 topic")

        for domain in domains:
            raise_if_cancel_requested()
            domain_name = domain.get("name", "")
            logger.info(f"[StudentAgent] === 领域: {domain_name} ===")

            for topic in domain.get("topics", []):
                raise_if_cancel_requested()
                topic_name = topic.get("name", "")
                topic_status = topic.get("status", "pending")
                stats["total"] += 1

                # 跳过已完成
                if topic_status == "done":
                    stats["skipped"] += 1
                    logger.info(f"  跳过已完成: {topic_name}")
                    processed_topics += 1
                    progress = 10 + int(processed_topics / max(total_topics, 1) * 82)
                    report_progress(progress, f"自动学习：跳过已完成 {processed_topics}/{total_topics} - {topic_name}")
                    continue

                logger.info(f"  开始学习: {topic_name}")
                progress = 10 + int(processed_topics / max(total_topics, 1) * 82)
                report_progress(progress, f"自动学习：学习 {processed_topics + 1}/{total_topics} - {topic_name}")

                # 标记状态
                ca.update_topic_status(domain_name, topic_name, "studying", curriculum_path)
                topic["status"] = "studying"

                # 收集搜索关键词
                queries = topic.get("search_queries", [])

                # 收集已知源 URL
                known_urls = [
                    s.get("url") for s in topic.get("known_sources", []) if s.get("url")
                ]

                try:
                    # 先学习已知源
                    for url in known_urls:
                        raise_if_cancel_requested()
                        if self.store.exists_by_url(url):
                            continue
                        source_type = self._detect_source_type(url)
                        try:
                            if source_type == "github":
                                await self.study_github(url)
                            elif source_type == "arxiv":
                                await self.study_arxiv(url)
                            elif source_type == "course":
                                await self.study_course(url, max_pages=30)
                            else:
                                await self._study_web_page(url)
                        except TaskCancellationRequested:
                            raise
                        except Exception as e:
                            logger.warning(f"  已知源学习失败 {url}: {e}")

                    # 再按主题搜索补充
                    raise_if_cancel_requested()
                    result = await self.study_topic(
                        topic_name, search_queries=queries, max_resources=5
                    )

                    if "error" in result and not result.get("material_ids"):
                        stats["failed"] += 1
                        ca.update_topic_status(domain_name, topic_name, "failed", curriculum_path)
                        topic["status"] = "failed"
                        logger.warning(f"  学习失败: {topic_name} - {result.get('error')}")
                    else:
                        stats["completed"] += 1
                        ca.update_topic_status(domain_name, topic_name, "done", curriculum_path)
                        topic["status"] = "done"

                        # 将发现的源写回 curriculum
                        discovered = topic.get("discovered_sources", [])
                        for mid in result.get("material_ids", []):
                            mat = self.store.get(mid)
                            if mat and mat.source_url:
                                discovered.append({
                                    "url": mat.source_url,
                                    "type": mat.source_type,
                                    "title": mat.title,
                                })
                        topic["discovered_sources"] = discovered
                        ca.save(curriculum, curriculum_path)

                        logger.info(
                            f"  完成: {topic_name} | "
                            f"素材={len(result.get('material_ids', []))}"
                        )

                except TaskCancellationRequested:
                    raise
                except Exception as e:
                    stats["failed"] += 1
                    ca.update_topic_status(domain_name, topic_name, "failed", curriculum_path)
                    topic["status"] = "failed"
                    logger.error(f"  主题学习异常: {topic_name} - {e}")
                finally:
                    processed_topics += 1
                    progress = 10 + int(processed_topics / max(total_topics, 1) * 82)
                    report_progress(progress, f"自动学习：已处理 {processed_topics}/{total_topics} - {topic_name}")

        # 更新总状态
        report_progress(95, "自动学习：更新课程表状态")
        curriculum = ca.load(curriculum_path)
        if curriculum:
            topic_statuses = [
                t.get("status")
                for d in curriculum.get("domains", [])
                for t in d.get("topics", [])
            ]
            all_finished = all(s in ("done", "failed") for s in topic_statuses)
            any_failed = any(s == "failed" for s in topic_statuses)
            if all_finished:
                curriculum["status"] = "completed_with_errors" if any_failed else "completed"
            else:
                curriculum["status"] = "in_progress"
            ca.save(curriculum, curriculum_path)

        logger.info(
            f"[StudentAgent] 课程表执行完成: "
            f"完成={stats['completed']}, 失败={stats['failed']}, "
            f"跳过={stats['skipped']}, 总计={stats['total']}"
        )
        report_progress(98, f"自动学习：完成={stats['completed']}，失败={stats['failed']}，跳过={stats['skipped']}")
        return stats

    async def _study_web_page(self, url: str) -> Dict:
        """学习普通网页（doc/web类型的降级处理）"""
        fetch_input = WorkerInput(
            url=url,
            metadata={"source_type": "web"},
        )
        fetch_output = self.fetcher.run(fetch_input)
        if not fetch_output.success:
            return {"error": fetch_output.error}

        mat = fetch_output.materials[0] if fetch_output.materials else Material(
            source_url=url, source_type="web", content=fetch_output.content
        )
        mat.source_type = "web"
        mat = await self._enrich_material(mat, fetch_output)
        mat_id = self.store.save(mat)
        return {"title": mat.title, "material_id": mat_id}

    def _detect_source_type(self, url: str) -> str:
        """检测URL类型"""
        if "github.com" in url:
            return "github"
        elif "arxiv.org" in url:
            return "arxiv"
        elif any(kw in url.lower() for kw in ("learn", "course", "tutorial")):
            return "course"
        else:
            return "web"
