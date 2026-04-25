import asyncio
import argparse
import signal
import re

import nest_asyncio
nest_asyncio.apply()

from src.agents.editor_agent import EditorAgent
from src.researchers.arxiv_researcher import ArxivResearcher
from src.researchers.wechat_reader import WechatReader
from src.researchers.doc_researcher import DocResearcher
from src.utils.logger import logger
from src.utils.task_manager import TaskManager


# Pipeline state container (avoids global mutable state)
class _PipelineHolder:
    instance = None

    @classmethod
    def get(cls):
        return cls.instance

    @classmethod
    def set(cls, pipeline):
        cls.instance = pipeline


def _sigint_handler(sig, frame):
    """Ctrl+C handler: set pause flag instead of killing the process."""
    pipeline = _PipelineHolder.get()
    if pipeline:
        logger.info("收到中断信号 (Ctrl+C)，流水线将在当前步骤完成后暂停...")
        pipeline.set_pause()
    else:
        raise KeyboardInterrupt


async def main():

    parser = argparse.ArgumentParser(description="AI 知识库自动出版系统")
    parser.add_argument("--mode", type=str, default="daily",
                        choices=[
                            # 旧模式（保留，向后兼容）
                            "daily", "wechat", "arxiv", "doc", "course", "queue", "resume", "status",
                            # 新模式（学生+出版社架构）
                            "study-course", "study-wechat", "study-github", "study-arxiv",
                            "study-topic",
                            "publish", "full",
                            # 自治模式（课程表驱动）
                            "curriculum", "auto-study",
                            # 工具模式
                            "materials",
                        ],
                        help="运行模式")
    parser.add_argument("--url", type=str, help="目标 URL")
    parser.add_argument("--query", type=str, help="搜索关键词")
    parser.add_argument("--topic", type=str, help="学习/出版主题")
    parser.add_argument("--max-pages", type=int, default=50, help="最大爬取页面数（默认 50）")
    parser.add_argument("--parent-id", type=str, help="限定父素材ID（publish 模式）")
    parser.add_argument("--depth", type=str, default="comprehensive",
                        choices=["quick", "comprehensive", "expert"],
                        help="课程表深度（curriculum 模式）")

    args = parser.parse_args()

    # ========== 无需初始化的模式 ==========
    if args.mode == "status":
        _show_pipeline_status()
        return

    if args.mode == "materials":
        _show_materials_status()
        return

    # ========== 新模式：学生智能体 ==========
    if args.mode.startswith("study-"):
        await _handle_study_mode(args)
        return

    # ========== 自治模式：课程表 ==========
    if args.mode == "curriculum":
        await _handle_curriculum_mode(args)
        return

    if args.mode == "auto-study":
        await _handle_auto_study_mode(args)
        return

    # ========== 新模式：出版社智能体 ==========
    if args.mode == "publish":
        await _handle_publish_mode(args)
        return

    # ========== 新模式：端到端 ==========
    if args.mode == "full":
        await _handle_full_mode(args)
        return

    # ========== 旧模式（向后兼容） ==========
    from src.graph.pipeline import KnowledgePipeline, STEP_NAMES, STEP_DISPLAY_NAMES

    editor = EditorAgent()
    await editor.initialize()
    pipeline = KnowledgePipeline(editor)
    _PipelineHolder.set(pipeline)
    task_manager = TaskManager()

    # Install Ctrl+C handler for graceful pause
    signal.signal(signal.SIGINT, _sigint_handler)

    if args.mode == "daily":
        logger.info("启动每日 ArXiv 论文更新...")
        arxiv_researcher = ArxivResearcher()
        papers = arxiv_researcher.fetch_daily_updates(max_results=3)

        for paper in papers:
            logger.info(f"正在处理论文: {paper['title']}")
            content = arxiv_researcher.download_and_parse(paper['pdf_url'], paper['title'])
            if not content:
                content = paper['summary']

            result = await pipeline.process(content, f"ArXiv: {paper['entry_id']}", paper['title'])
            _log_result(result)
            if result.status == "paused":
                logger.info("流水线已暂停，停止处理后续论文")
                break

    elif args.mode == "wechat":
        if not args.url:
            print("请提供 --url 参数")
            return

        reader = WechatReader()
        article_data = reader.process_article(args.url)

        if "error" in article_data:
            print(f"错误: {article_data['error']}")
            return

        full_content = article_data['content']
        for interp in article_data.get('image_interpretations', []):
            full_content += f"\n\n图片分析 ({interp['url']}):\n{interp['description']}"
        for repo in article_data.get('related_repos', []):
            full_content += f"\n\n关联 GitHub 仓库: {repo.get('name')}\n{repo.get('description')}\n{repo.get('readme', '')[:2000]}"

        result = await pipeline.process(full_content, args.url, article_data.get('title', '微信文章'))
        _log_result(result)

    elif args.mode == "arxiv":
        if not args.query:
            print("请提供 --query 参数")
            return

        arxiv_researcher = ArxivResearcher()
        papers = arxiv_researcher.search_papers(args.query, max_results=1)
        if papers:
            paper = papers[0]
            content = arxiv_researcher.download_and_parse(paper['pdf_url'], paper['title'])
            if not content:
                content = paper['summary']
            result = await pipeline.process(content, paper['entry_id'], paper['title'])
            _log_result(result)
        else:
            logger.warning(f"未找到与 '{args.query}' 相关的论文")

    elif args.mode == "doc":
        if not args.url:
            print("请提供 --url 参数")
            return

        researcher = DocResearcher()
        doc_data = researcher.research_doc(args.url, max_depth=1, max_pages=3)

        full_content = f"文档根地址: {doc_data['root_url']}\n\n"
        for page in doc_data['pages']:
            full_content += f"页面: {page['url']}\n标题: {page['title']}\n内容:\n{page['content']}\n\n"

        if doc_data.get('skipped', 0) > 0:
            logger.info(f"增量学习: 跳过了 {doc_data['skipped']} 个未变化的页面")

        result = await pipeline.process(full_content, args.url, "技术文档分析")
        _log_result(result)

    elif args.mode == "course":
        if not args.url:
            print("请提供 --url 参数")
            return

        researcher = DocResearcher()
        doc_data = researcher.research_course(args.url, max_depth=3, max_pages=args.max_pages)

        full_content = f"课程根地址: {doc_data['root_url']}\n\n"
        for page in doc_data['pages']:
            full_content += f"## 第 {page['order']+1} 章: {page['title']}\n"
            full_content += f"URL: {page['url']}\n\n{page['content']}\n\n---\n\n"

        if doc_data.get('skipped', 0) > 0:
            logger.info(f"增量学习: 跳过了 {doc_data['skipped']} 个未变化的页面")

        course_title = "在线课程"
        if doc_data.get('page_order') and len(doc_data['page_order']) > 0:
            course_title = doc_data['page_order'][0].get('title', '在线课程')

        logger.info(f"课程共 {len(doc_data['pages'])} 个页面")
        result = await pipeline.process(full_content, args.url, course_title)
        _log_result(result)

    elif args.mode == "queue":
        logger.info("启动队列处理模式...")
        pending_urls = task_manager.get_pending_urls()

        if not pending_urls:
            logger.info("待处理队列为空")
            return

        reader = WechatReader()
        arxiv_researcher = ArxivResearcher()

        for url in pending_urls:
            if pipeline.is_paused():
                logger.info("流水线已暂停，停止处理队列")
                break

            logger.info(f"正在处理队列中的 URL: {url}")

            try:
                # 检查是否有已存在的检查点
                thread_id = KnowledgePipeline.make_thread_id(url)
                existing = pipeline.get_status(thread_id)

                if existing and existing.status in ("paused", "error"):
                    logger.info(f"恢复已有检查点: {url} (step {existing.current_step})")
                    content = existing.content
                    title = existing.topic
                else:
                    content, title = _fetch_content(url, reader, arxiv_researcher)

                result = await pipeline.process(content, url, title)
                _log_result(result)

                if result.status == "completed":
                    task_manager.mark_as_processed(url)
                elif result.status == "paused":
                    logger.info("流水线已暂停，停止处理队列")
                    break

            except Exception as e:
                logger.error(f"处理 {url} 时出错: {e}")

    elif args.mode == "resume":
        logger.info("启动恢复模式...")
        pipeline.clear_pause()
        all_states = pipeline.list_pipelines()
        resumable = [s for s in all_states if s.status in ("paused", "running", "error")]

        if not resumable:
            logger.info("无已暂停/中断的任务")
            return

        logger.info(f"发现 {len(resumable)} 个可恢复的任务")
        for state in resumable:
            if pipeline.is_paused():
                logger.info("流水线已暂停，停止恢复")
                break

            step_name = STEP_DISPLAY_NAMES[state.current_step] if state.current_step < len(STEP_DISPLAY_NAMES) else "?"
            logger.info(f"恢复任务: {state.source} (步骤 {state.current_step}/{len(STEP_NAMES)}: {step_name})")

            result = await pipeline.process(state.content, state.source, state.topic)
            _log_result(result)

            if result.status == "completed":
                task_manager.mark_as_processed(state.source)
            elif result.status == "paused":
                logger.info("流水线已暂停，停止恢复后续任务")
                break

    logger.info("处理完成")


# ==================== 新模式处理函数 ====================

async def _handle_study_mode(args):
    """处理 study-* 模式"""
    from src.student.student_agent import StudentAgent

    student = StudentAgent()
    mode = args.mode

    if mode == "study-course":
        if not args.url:
            print("请提供 --url 参数")
            return
        result = await student.study_course(args.url, max_pages=args.max_pages)

    elif mode == "study-wechat":
        if not args.url:
            print("请提供 --url 参数")
            return
        result = await student.study_wechat(args.url)

    elif mode == "study-github":
        if not args.url:
            print("请提供 --url 参数")
            return
        result = await student.study_github(args.url)

    elif mode == "study-arxiv":
        if not args.url and not args.query:
            print("请提供 --url 或 --query 参数")
            return
        url = args.url
        if not url and args.query:
            # 搜索ArXiv论文
            from src.researchers.arxiv_researcher import ArxivResearcher
            arxiv = ArxivResearcher()
            papers = arxiv.search_papers(args.query, max_results=1)
            if papers:
                url = papers[0].get("entry_id", "")
            else:
                print(f"未找到与 '{args.query}' 相关的论文")
                return
        result = await student.study_arxiv(url)

    elif mode == "study-topic":
        if not args.topic:
            print("请提供 --topic 参数（学习主题）")
            return
        result = await student.study_topic(args.topic)

    else:
        print(f"未知的学习模式: {mode}")
        return

    # 输出结果
    if "error" in result:
        logger.error(f"学习失败: {result['error']}")
    else:
        logger.info(f"学习完成: {result.get('title', '未知')}")
        if "material_ids" in result:
            logger.info(f"  素材数: {len(result['material_ids'])}")
        if "material_id" in result:
            logger.info(f"  素材ID: {result['material_id']}")
        if "ref_materials" in result:
            logger.info(f"  引用追踪: {len(result['ref_materials'])}个")


async def _handle_publish_mode(args):
    """处理 publish 模式"""
    from src.publisher_v2.publisher_agent import PublisherAgent

    if not args.topic:
        print("请提供 --topic 参数（出版主题）")
        return

    publisher = PublisherAgent()
    result = await publisher.publish_book(
        topic=args.topic,
        parent_id=args.parent_id,
    )

    if "error" in result:
        logger.error(f"出版失败: {result['error']}")
    else:
        logger.info(f"出版完成: {result.get('title', '')}")
        logger.info(f"  输出目录: {result.get('output_dir', '')}")
        logger.info(f"  章节数: {result.get('chapters', 0)}")
        logger.info(f"  小节数: {result.get('sections', 0)}")
        logger.info(f"  文件数: {result.get('files', 0)}")


async def _handle_full_mode(args):
    """处理 full 模式：先学习再出版"""
    from src.student.student_agent import StudentAgent
    from src.publisher_v2.publisher_agent import PublisherAgent

    if not args.url:
        print("请提供 --url 参数")
        return

    # 1. 学习阶段
    student = StudentAgent()
    url = args.url

    # 自动检测URL类型
    if "github.com" in url:
        study_result = await student.study_github(url)
    elif "arxiv.org" in url:
        study_result = await student.study_arxiv(url)
    elif "mp.weixin.qq.com" in url:
        study_result = await student.study_wechat(url)
    elif any(kw in url.lower() for kw in ["learn", "course", "tutorial"]):
        study_result = await student.study_course(url, max_pages=args.max_pages)
    else:
        study_result = await student.study_wechat(url)  # 默认当做网页处理

    if "error" in study_result:
        logger.error(f"学习阶段失败: {study_result['error']}")
        return

    logger.info(f"学习阶段完成: {study_result.get('title', '')}")

    # 2. 出版阶段
    topic = args.topic or study_result.get("title", "知识库")
    parent_id = study_result.get("parent_id", study_result.get("material_id", ""))

    publisher = PublisherAgent()
    pub_result = await publisher.publish_book(
        topic=topic,
        parent_id=parent_id,
    )

    if "error" in pub_result:
        logger.error(f"出版阶段失败: {pub_result['error']}")
    else:
        logger.info(f"端到端完成!")
        logger.info(f"  书名: {pub_result.get('title', '')}")
        logger.info(f"  输出: {pub_result.get('output_dir', '')}")
        logger.info(f"  {pub_result.get('chapters', 0)}章, {pub_result.get('sections', 0)}节")


async def _handle_curriculum_mode(args):
    """处理 curriculum 模式：生成课程表"""
    from src.student.curriculum_agent import CurriculumAgent

    if not args.topic:
        print("请提供 --topic 参数（学习方向，如 'LLM全栈工程师'）")
        return

    ca = CurriculumAgent()
    curriculum = ca.generate(goal=args.topic, depth=args.depth)

    # 打印课程表摘要
    domains = curriculum.get("domains", [])
    total_topics = sum(len(d.get("topics", [])) for d in domains)
    total_sources = sum(
        len(t.get("known_sources", []))
        for d in domains for t in d.get("topics", [])
    )

    print(f"\n课程表已生成并保存到 config/curriculum.yaml")
    print(f"  学习方向: {curriculum.get('goal')}")
    print(f"  深度: {curriculum.get('depth')}")
    print(f"  领域数: {len(domains)}")
    print(f"  主题数: {total_topics}")
    print(f"  预置源匹配: {total_sources}")
    print()

    for domain in domains:
        print(f"  [{domain.get('priority', '?')}] {domain.get('name')}")
        for topic in domain.get("topics", []):
            sources_count = len(topic.get("known_sources", []))
            src_hint = f" ({sources_count}个预置源)" if sources_count else ""
            print(f"      - [{topic.get('difficulty', '?')}] {topic.get('name')}{src_hint}")

    print(f"\n状态: {curriculum.get('status')}")
    print("请审核后运行 --mode auto-study 开始自动学习")
    print("也可以编辑 config/curriculum.yaml 调整后再运行")


async def _handle_auto_study_mode(args):
    """处理 auto-study 模式：按课程表自动学习"""
    from src.student.curriculum_agent import CurriculumAgent
    from src.student.student_agent import StudentAgent

    ca = CurriculumAgent()
    curriculum = ca.load()

    if not curriculum:
        print("未找到课程表。请先运行 --mode curriculum --topic '学习方向' 生成课程表")
        return

    status = curriculum.get("status", "draft")

    # 自动批准 draft 状态的课程表
    if status == "draft":
        logger.info("课程表状态为 draft，自动批准...")
        ca.approve()

    elif status == "completed":
        print("课程表已全部学习完成")
        progress = ca.get_progress()
        print(f"  总计: {progress['total']}  完成: {progress['done']}  "
              f"进行中: {progress['studying']}  待学: {progress['pending']}")
        return

    elif status not in ("approved", "in_progress"):
        print(f"课程表状态异常: {status}")
        return

    # 显示进度
    progress = ca.get_progress()
    logger.info(
        f"课程表进度: 总计 {progress['total']}, 完成 {progress['done']}, "
        f"进行中 {progress['studying']}, 待学 {progress['pending']}"
    )

    # 执行自动学习
    student = StudentAgent()
    result = await student.study_curriculum()

    if "error" in result:
        logger.error(f"自动学习失败: {result['error']}")
    else:
        logger.info("自动学习完成!")
        logger.info(f"  完成: {result.get('completed', 0)}")
        logger.info(f"  失败: {result.get('failed', 0)}")
        logger.info(f"  跳过: {result.get('skipped', 0)}")
        logger.info(f"  总计: {result.get('total', 0)}")


# ==================== 工具函数 ====================

def _fetch_content(url: str, reader: WechatReader, arxiv_researcher: ArxivResearcher) -> tuple:
    """根据 URL 类型获取内容，返回 (content, title)"""
    if "mp.weixin.qq.com" in url:
        article_data = reader.process_article(url)
        if "error" in article_data:
            raise Exception(article_data['error'])
        full_content = article_data['content']
        for interp in article_data.get('image_interpretations', []):
            full_content += f"\n\n图片分析 ({interp['url']}):\n{interp['description']}"
        for repo in article_data.get('related_repos', []):
            full_content += f"\n\n关联 GitHub 仓库: {repo.get('name')}\n{repo.get('description')}\n{repo.get('readme', '')[:2000]}"
        return full_content, article_data.get('title', '微信文章')

    elif "arxiv.org" in url:
        arxiv_id_match = re.search(r'(\d{4}\.\d{4,5})', url)
        if arxiv_id_match:
            arxiv_id = arxiv_id_match.group(1)
            papers = arxiv_researcher.search_papers(arxiv_id, max_results=1)
            if papers:
                paper = papers[0]
                content = arxiv_researcher.download_and_parse(paper['pdf_url'], paper['title'])
                if not content:
                    content = paper['summary']
                return content, paper['title']
        raise Exception(f"无法从 URL 提取或查找 ArXiv 论文: {url}")

    else:
        doc_researcher = DocResearcher()
        html = doc_researcher.browser.fetch_page(url)
        if html:
            text = doc_researcher.browser.extract_text(html)
            title = doc_researcher.browser.extract_title(html)
            return text, title or "网页文章"
        raise Exception(f"无法获取页面内容: {url}")


def _log_result(result):
    """Log pipeline result."""
    from src.graph.pipeline import STEP_NAMES, STEP_DISPLAY_NAMES
    if result.status == "completed":
        logger.info(f"流水线完成: {result.output_path}")
    elif result.status == "paused":
        step_name = STEP_DISPLAY_NAMES[result.current_step] if result.current_step < len(STEP_DISPLAY_NAMES) else "?"
        logger.info(f"流水线已暂停于步骤 {result.current_step}/{len(STEP_NAMES)}: {step_name}")
    elif result.status == "error":
        logger.error(f"流水线出错: {result.error_message}")


def _show_pipeline_status():
    """Show all pipeline checkpoint statuses."""
    from src.graph.pipeline import PipelineCheckpointer, STEP_NAMES, STEP_DISPLAY_NAMES
    checkpointer = PipelineCheckpointer()
    all_states = checkpointer.list_all()

    if not all_states:
        print("无流水线记录")
        return

    print(f"{'Thread ID':<14} {'状态':<12} {'步骤':<8} {'来源URL':<50}")
    print("-" * 84)
    for s in all_states:
        step_info = f"{s.current_step}/{len(STEP_NAMES)}"
        source_short = s.source[:48] + ".." if len(s.source) > 50 else s.source
        print(f"{s.thread_id:<14} {s.status:<12} {step_info:<8} {source_short}")


def _show_materials_status():
    """Show material store statistics."""
    from src.core.material_store import MaterialStore
    store = MaterialStore()

    total = store.count()
    print(f"\n素材库统计:")
    print(f"  总素材数: {total}")

    for stype in ["course", "course_page", "wechat", "github", "arxiv", "doc_page", "web"]:
        count = store.count(source_type=stype)
        if count > 0:
            print(f"  {stype}: {count}")

    tags = store.list_all_tags()
    if tags:
        print(f"\n  标签 ({len(tags)}): {', '.join(tags[:20])}")
        if len(tags) > 20:
            print(f"    ... 和 {len(tags) - 20} 个更多标签")


if __name__ == "__main__":
    asyncio.run(main())
