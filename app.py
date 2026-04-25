import streamlit as st
import os
import glob
import json
import asyncio
from datetime import datetime

from src.core.llm_presets import list_presets, detect_preset, apply_preset_to_settings
from src.utils.task_manager import TaskManager
from src.utils.logger import logger
from src.core.material_store import MaterialStore


def inject_global_styles():
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f6f5f4;
            --panel-bg: rgba(255,255,255,0.92);
            --panel-strong: #ffffff;
            --text-main: rgba(0,0,0,0.92);
            --text-soft: #6b645f;
            --line-soft: rgba(0,0,0,0.08);
            --accent: #0075de;
            --accent-soft: #eff6ff;
            --success-bg: #edf8f1;
            --warn-bg: #fff5e8;
            --danger-bg: #fff0ef;
            --radius-lg: 18px;
            --radius-md: 12px;
            --shadow-soft: 0 20px 50px rgba(15, 23, 42, 0.06);
        }
        .stApp {
            background: linear-gradient(180deg, #fbfaf9 0%, var(--app-bg) 100%);
            color: var(--text-main);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f7f5f3 100%);
            border-right: 1px solid var(--line-soft);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        .stMarkdown p,
        .stCaption {
            color: var(--text-soft);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        .app-hero {
            background: radial-gradient(circle at top right, rgba(0,117,222,0.10), transparent 30%), var(--panel-bg);
            border: 1px solid rgba(255,255,255,0.75);
            box-shadow: var(--shadow-soft);
            border-radius: 24px;
            padding: 1.4rem 1.5rem 1.2rem 1.5rem;
            margin-bottom: 1rem;
        }
        .app-kicker {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            margin-bottom: 0.7rem;
        }
        .app-hero h1 {
            margin: 0;
            font-size: 2.2rem;
            line-height: 1.05;
            color: var(--text-main);
        }
        .app-hero p {
            margin: 0.6rem 0 0 0;
            max-width: 900px;
            font-size: 1rem;
            line-height: 1.7;
            color: var(--text-soft);
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.85rem;
            margin: 0.8rem 0 1rem 0;
        }
        .metric-card {
            background: var(--panel-strong);
            border: 1px solid var(--line-soft);
            border-radius: 16px;
            padding: 1rem 1rem 0.95rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }
        .metric-card .label {
            font-size: 0.82rem;
            color: var(--text-soft);
            margin-bottom: 0.45rem;
        }
        .metric-card .value {
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text-main);
        }
        .surface-card {
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.04);
            margin: 0.8rem 0;
        }
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.28rem 0.72rem;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.5rem;
        }
        .status-chip.success { background: var(--success-bg); color: #107c41; }
        .status-chip.partial { background: var(--warn-bg); color: #b85d00; }
        .status-chip.error { background: var(--danger-bg); color: #c0392b; }
        .status-chip.info { background: var(--accent-soft); color: var(--accent); }
        .list-item {
            padding: 0.8rem 0.9rem;
            border-radius: 14px;
            border: 1px solid rgba(0,0,0,0.05);
            background: rgba(255,255,255,0.82);
            margin-bottom: 0.55rem;
        }
        .list-item strong { color: var(--text-main); }
        .inline-note {
            padding: 0.75rem 0.9rem;
            border-left: 4px solid var(--accent);
            background: var(--accent-soft);
            border-radius: 10px;
            margin: 0.8rem 0;
            color: #0f3b65;
            font-size: 0.92rem;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.08);
            min-height: 2.8rem;
            font-weight: 600;
            box-shadow: 0 8px 18px rgba(15,23,42,0.04);
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stNumberInput input {
            border-radius: 12px !important;
            border-color: rgba(0,0,0,0.12) !important;
            background: rgba(255,255,255,0.92) !important;
        }
        [data-testid="stExpander"] {
            border-radius: 16px;
            border: 1px solid rgba(0,0,0,0.06);
            background: rgba(255,255,255,0.85);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding-left: 1rem;
            padding-right: 1rem;
            background: rgba(255,255,255,0.62);
        }
        .stTabs [aria-selected="true"] {
            background: var(--accent-soft) !important;
            color: var(--accent) !important;
        }
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #3da1ff 0%, #0075de 100%);
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: var(--text-main);
            letter-spacing: -0.01em;
        }
        .stMarkdown h2 {
            margin-top: 1.4rem;
            border-bottom: 1px solid rgba(0,0,0,0.08);
            padding-bottom: 0.35rem;
        }
        .stMarkdown blockquote {
            margin: 1rem 0;
            padding: 0.8rem 1rem;
            background: #f7fbff;
            border-left: 4px solid var(--accent);
            border-radius: 10px;
            color: #38546f;
        }
        .stMarkdown code {
            border-radius: 8px;
            padding: 0.15rem 0.35rem;
            background: #f1f3f5;
        }
        .stMarkdown pre code {
            background: transparent;
            padding: 0;
        }
        .stAlert {
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(title: str, subtitle: str, kicker: str = "学习项目工作台"):
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-kicker">{kicker}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(items):
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div></div>'
        )
    if cards:
        st.markdown(f'<div class="metric-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_status_chip(label: str, kind: str = "info"):
    st.markdown(f'<span class="status-chip {kind}">{label}</span>', unsafe_allow_html=True)


def render_list_item(title: str, body: str = ""):
    body_html = f"<div style=\"margin-top:0.2rem;color:var(--text-soft);\">{body}</div>" if body else ""
    st.markdown(f'<div class="list-item"><strong>{title}</strong>{body_html}</div>', unsafe_allow_html=True)


def render_inline_note(text: str):
    st.markdown(f'<div class="inline-note">{text}</div>', unsafe_allow_html=True)


def run_async(coro):
    """
    在 Streamlit 环境下安全执行 async 协程。
    优先使用已有的 event loop（Streamlit 场景），必要时 fallback 到 nest_asyncio。
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Streamlit 环境下 loop 已运行，需要 nest_asyncio
            import nest_asyncio
            nest_asyncio.apply(loop)
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 没有 event loop，创建新的
        return asyncio.run(coro)

# --- 页面配置 ---
st.set_page_config(
    page_title="AI 知识库自动出版系统",
    page_icon="📚",
    layout="wide"
)

# --- 全局常量 ---
inject_global_styles()
KB_ROOT = "knowledge_base"
LOG_DIR = "data/logs"
MATERIAL_DIR = "data/materials"
TASK_MANAGER = TaskManager()

# --- session_state 初始化 ---
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "process_log" not in st.session_state:
    st.session_state.process_log = []  # [{url, status, message}]
if "study_result" not in st.session_state:
    st.session_state.study_result = None
if "publish_result" not in st.session_state:
    st.session_state.publish_result = None
if "curriculum" not in st.session_state:
    st.session_state.curriculum = None
if "curriculum_progress" not in st.session_state:
    st.session_state.curriculum_progress = None
if "curriculum_error" not in st.session_state:
    st.session_state.curriculum_error = None
if "auto_study_result" not in st.session_state:
    st.session_state.auto_study_result = None


def _load_publish_report(book_path: str):
    report_path = os.path.join(book_path, "publish_report.json")
    if not os.path.exists(report_path):
        return None
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"读取出版报告失败 {report_path}: {e}")
        return None


def _render_publish_result(result: dict):
    if not result:
        return

    status = result.get("status", "success")
    title = result.get("title", "未命名书籍")
    output_dir = result.get("output_dir", "")
    completed = result.get("completed_sections", result.get("sections", 0))
    expected = result.get("expected_sections", result.get("sections", 0))
    warnings = result.get("warnings", [])
    missing = result.get("missing_sections", [])

    chip_kind = "success" if status == "success" else "partial" if status == "partial" else "error"
    render_status_chip(f"出版状态: {status}", chip_kind)
    st.markdown(f"### {title}")
    render_metric_cards([
        ("完成小节", completed),
        ("预期小节", expected),
        ("质量提醒", len(warnings)),
    ])
    if output_dir:
        render_inline_note(f"输出目录：{output_dir}")

    if missing:
        with st.expander(f"缺失小节 ({len(missing)})", expanded=status != "success"):
            for item in missing:
                render_list_item(
                    f"{item.get('chapter', '')} / {item.get('section', '')}",
                    item.get('reason', ''),
                )

    if warnings:
        with st.expander(f"质量提醒 ({len(warnings)})", expanded=status == "partial"):
            for warning in warnings[:30]:
                render_list_item(warning)


def main():
    st.sidebar.title("📚 AI 知识库")

    # 全局处理状态横幅
    if st.session_state.is_processing:
        st.sidebar.warning("⏳ 正在处理任务中...")

    page = st.sidebar.radio(
        "导航",
        ["📖 知识库浏览", "📦 素材库", "🎓 学习任务", "📕 出版任务",
         "🔗 任务中心", "📝 运行日志", "⚙️ 系统设置"]
    )

    # 任何页面顶部显示全局处理状态横幅
    if st.session_state.is_processing:
        st.info("🔄 后台正在处理任务，请勿关闭页面。切换页面不会中断处理。")

    if page == "📖 知识库浏览":
        page_knowledge_base()
    elif page == "📦 素材库":
        page_material_store()
    elif page == "🎓 学习任务":
        page_study_tasks()
    elif page == "📕 出版任务":
        page_publish_tasks()
    elif page == "🔗 任务中心":
        page_task_center()
    elif page == "📝 运行日志":
        page_logs()
    elif page == "⚙️ 系统设置":
        page_settings()


# ==================== 知识库浏览 ====================
def page_knowledge_base():
    render_page_hero(
        "📖 知识库浏览",
        "按书籍、章节和小节查看生成内容，同时检查出版完整性、质量提醒与最终阅读效果。",
        kicker="知识内容体验",
    )

    if not os.path.exists(KB_ROOT):
        st.warning("知识库目录不存在")
        return

    # 获取所有分类目录（书籍）
    categories = sorted([
        d for d in os.listdir(KB_ROOT)
        if os.path.isdir(os.path.join(KB_ROOT, d))
    ])

    if not categories:
        st.info("知识库暂无分类目录")
        return

    # 侧边栏选择书籍
    selected_cat = st.sidebar.selectbox("选择书籍/分类", categories)

    if not selected_cat:
        return

    cat_path = os.path.join(KB_ROOT, selected_cat)
    st.subheader(f"📁 {selected_cat}")

    report = _load_publish_report(cat_path)
    if report:
        render_metric_cards([
            ("完成小节", report.get("completed_sections", 0)),
            ("预期小节", report.get("expected_sections", 0)),
            ("质量提醒", len(report.get("warnings", []))),
        ])
        status = report.get("status", "success")
        if status == "partial":
            st.warning("这本书包含部分失败或质量风险，建议优先查看 README 中的出版质量概览。")
        elif status == "success":
            st.caption("这本书通过了完整性检查。")

    # 检测目录结构：是否有子目录（嵌套结构）
    sub_dirs = sorted([
        d for d in os.listdir(cat_path)
        if os.path.isdir(os.path.join(cat_path, d))
    ])
    top_md_files = sorted(glob.glob(os.path.join(cat_path, "*.md")))

    if sub_dirs:
        # ---- 嵌套结构：书籍 → 章节 → 小节 ----
        # 侧边栏选择章节
        selected_chapter = st.sidebar.selectbox("选择章节", sub_dirs)

        if selected_chapter:
            chapter_path = os.path.join(cat_path, selected_chapter)
            section_files = sorted(glob.glob(os.path.join(chapter_path, "*.md")))

            st.markdown(f"**📂 {selected_chapter}**")

            if not section_files:
                st.info("该章节下暂无文章")
            else:
                section_names = [os.path.basename(f) for f in section_files]
                selected_section = st.selectbox("选择小节", section_names)

                if selected_section:
                    file_path = os.path.join(chapter_path, selected_section)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    st.markdown("---")
                    render_inline_note("正文中的轻量来源标记会提示本节主要依据；文末的“来源与延伸阅读”用于追溯原始材料。")
                    st.markdown(content)

                    mtime = os.path.getmtime(file_path)
                    st.caption(f"最后修改: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")

        # 同时显示顶层 md 文件（如 README.md）
        if top_md_files:
            with st.expander(f"📄 顶层文件（{len(top_md_files)} 个）"):
                top_names = [os.path.basename(f) for f in top_md_files]
                selected_top = st.selectbox("选择文件", top_names, key="top_md_select")
                if selected_top:
                    fpath = os.path.join(cat_path, selected_top)
                    with open(fpath, "r", encoding="utf-8") as f:
                        render_inline_note("如果这是出版产物，正文来源提示与文末延伸阅读会一起展示，方便检查内容可信度。")
                        st.markdown(f.read())

    elif top_md_files:
        # ---- 扁平结构（旧格式）：分类下直接是 .md 文件 ----
        file_names = [os.path.basename(f) for f in top_md_files]
        selected_file = st.selectbox("选择文章", file_names)

        if selected_file:
            file_path = os.path.join(cat_path, selected_file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            st.markdown("---")
            render_inline_note("正文中的轻量来源标记会提示本节主要依据；文末的“来源与延伸阅读”用于追溯原始材料。")
            st.markdown(content)

            mtime = os.path.getmtime(file_path)
            st.caption(f"最后修改: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("该分类下暂无内容")


# ==================== 素材库浏览 ====================
def page_material_store():
    render_page_hero(
        "📦 素材库浏览",
        "查看已沉淀的课程页、论文、仓库和网页素材，检查元信息是否完整并为后续出版做准备。",
        kicker="素材资产总览",
    )

    store = _get_material_store()
    total = store.count()
    render_metric_cards([("当前素材总数", total)])

    if total == 0:
        st.info("素材库为空。请先通过「学习任务」页面收集素材。")
        return

    # ---- 统计概览 ----
    type_counts = {}
    for stype in ("course", "course_page", "wechat", "github", "arxiv", "doc_page", "web"):
        c = store.count(source_type=stype)
        if c > 0:
            type_counts[stype] = c

    render_metric_cards(
        [("总素材数", total)] + [(stype, cnt) for stype, cnt in type_counts.items()]
    )

    st.markdown("---")

    # ---- 筛选器 ----
    col_type, col_kw = st.columns([1, 3])
    with col_type:
        filter_type = st.selectbox("按类型筛选", ["全部"] + list(type_counts.keys()))
    with col_kw:
        filter_kw = st.text_input("关键词搜索", placeholder="输入标题关键词...")

    query_kwargs = {"limit": 200}
    if filter_type != "全部":
        query_kwargs["source_type"] = filter_type
    if filter_kw:
        query_kwargs["keyword"] = filter_kw

    materials = store.query(**query_kwargs)

    if not materials:
        st.info("未找到匹配的素材")
        return

    st.caption(f"共 {len(materials)} 条素材")

    # ---- 标签云 ----
    all_tags = store.list_all_tags()
    if all_tags:
        with st.expander("标签总览"):
            st.write(" | ".join(all_tags))

    # ---- 素材列表 ----
    for mat in materials:
        type_icon = {
            "course": "📘", "course_page": "📄", "wechat": "💬",
            "github": "🐙", "arxiv": "📑", "doc_page": "📃", "web": "🌐",
        }.get(mat.source_type, "📎")

        with st.expander(f"{type_icon} {mat.title or '(无标题)'} — {mat.source_type}"):
            st.caption(f"ID: `{mat.id}` | URL: {mat.source_url}")
            if mat.tags:
                st.caption(f"标签: {', '.join(mat.tags)}")
            if mat.terms:
                st.caption(f"术语: {', '.join(mat.terms[:10])}")
            if mat.summary:
                st.write(mat.summary[:300])
            st.caption(
                f"创建: {datetime.fromtimestamp(mat.created_at).strftime('%Y-%m-%d %H:%M') if mat.created_at else '—'}"
            )

            # 查看完整内容按钮
            if st.button("查看完整内容", key=f"view_{mat.id}"):
                full_mat = store.get(mat.id)
                if full_mat and full_mat.content:
                    st.markdown("---")
                    st.markdown(full_mat.content[:5000])
                    if len(full_mat.content) > 5000:
                        st.caption(f"（已截断显示，完整内容 {len(full_mat.content)} 字符）")

            # 查看图片
            if mat.images:
                img_count = len(mat.images)
                st.caption(f"图片: {img_count} 张")

            # 查看代码块
            if mat.code_blocks:
                st.caption(f"代码块: {len(mat.code_blocks)} 个")

            # 删除按钮
            if st.button("删除", key=f"del_{mat.id}"):
                store.delete(mat.id)
                st.rerun()


# ==================== 学习任务 ====================
def page_study_tasks():
    render_page_hero(
        "🎓 学习任务",
        "用学生智能体抓取课程、论文、仓库和主题资料，把外部知识源转成可复用的学习素材。",
        kicker="学生智能体",
    )

    is_busy = st.session_state.is_processing

    # 两个标签页：自治模式 vs 手动模式
    tab_auto, tab_manual = st.tabs(["自治学习（推荐）", "手动学习（指定URL）"])

    # ==================== 标签1: 自治学习 ====================
    with tab_auto:
        st.markdown(
            "输入一个学习方向，系统自动生成课程表 → 审核 → 全自动搜索资源并学习。"
        )

        # ---- 第1步: 生成课程表 ----
        st.subheader("1. 生成课程表")

        col_goal, col_depth = st.columns([3, 1])
        with col_goal:
            goal = st.text_input(
                "学习方向",
                placeholder="例如：LLM全栈工程师、计算机视觉、AI Agent开发...",
                disabled=is_busy,
                key="curriculum_goal",
            )
        with col_depth:
            depth = st.selectbox(
                "深度",
                ["quick (5-10主题)", "comprehensive (15-25主题)", "expert (30-50主题)"],
                index=1,
                disabled=is_busy,
                key="curriculum_depth",
            )
        depth_key = depth.split(" ")[0]

        if st.button("生成课程表", type="primary", disabled=is_busy or not goal,
                      key="gen_curriculum_btn"):
            _run_generate_curriculum(goal, depth_key)

        if st.session_state.curriculum_error:
            st.error(f"最近一次课程表生成失败: {st.session_state.curriculum_error}")
            st.caption("可到“📝 运行日志”页面查看详细日志。")

        # ---- 第2步: 显示/编辑课程表 ----
        curriculum = st.session_state.curriculum
        if curriculum is None:
            # 尝试从文件加载已有课程表
            curriculum = _load_existing_curriculum()
            if curriculum:
                st.session_state.curriculum = curriculum

        if curriculum:
            st.markdown("---")
            st.subheader("2. 审核课程表")

            status = curriculum.get("status", "draft")
            status_colors = {
                "draft": "orange", "approved": "green",
                "in_progress": "blue", "completed": "green",
            }
            st.markdown(
                f"**学习方向:** {curriculum.get('goal', '?')} &nbsp;|&nbsp; "
                f"**深度:** {curriculum.get('depth', '?')} &nbsp;|&nbsp; "
                f"**状态:** :{status_colors.get(status, 'gray')}[{status}]"
            )

            domains = curriculum.get("domains", [])
            total_topics = sum(len(d.get("topics", [])) for d in domains)
            total_sources = sum(
                len(t.get("known_sources", []))
                for d in domains for t in d.get("topics", [])
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("领域数", len(domains))
            c2.metric("主题数", total_topics)
            c3.metric("预置源匹配", total_sources)

            # 显示领域和主题
            for domain in domains:
                priority = domain.get("priority", "?")
                with st.expander(
                    f"[{priority}] {domain.get('name', '?')} — "
                    f"{len(domain.get('topics', []))}个主题"
                ):
                    if domain.get("description"):
                        st.caption(domain["description"])

                    for topic in domain.get("topics", []):
                        t_status = topic.get("status", "pending")
                        t_icon = {"done": "✅", "studying": "🔄", "pending": "⏳",
                                  "failed": "❌"}.get(t_status, "⏳")
                        diff = topic.get("difficulty", "?")
                        diff_badge = {"beginner": "🟢", "intermediate": "🟡",
                                      "advanced": "🔴"}.get(diff, "⚪")

                        st.markdown(
                            f"{t_icon} {diff_badge} **{topic.get('name', '?')}** "
                            f"({diff}) — {t_status}"
                        )
                        if topic.get("description"):
                            st.caption(f"  {topic['description']}")
                        if topic.get("known_sources"):
                            for src in topic["known_sources"]:
                                st.caption(f"  📎 [{src.get('name', '')}]({src.get('url', '')})")
                        if topic.get("search_queries"):
                            st.caption(f"  🔍 {', '.join(topic['search_queries'])}")

            # ---- 第3步: 批准 + 开始自动学习 ----
            st.markdown("---")
            st.subheader("3. 开始学习")

            col_approve, col_start = st.columns(2)

            with col_approve:
                if status == "draft":
                    if st.button("批准课程表", type="secondary", disabled=is_busy,
                                  key="approve_btn"):
                        _approve_curriculum()
                elif status == "approved":
                    st.success("课程表已批准，可以开始学习")
                elif status == "in_progress":
                    if is_busy:
                        st.info("学习任务正在当前会话中执行")
                    else:
                        st.warning("课程表状态仍是 in_progress，但当前并没有检测到正在执行的前台任务。这通常表示上次执行被中断了；可以点击右侧按钮继续自动学习。")
                elif status == "completed":
                    st.success("课程表已全部学习完成!")
                elif status == "completed_with_errors":
                    st.warning("课程表执行结束，但部分主题失败。可以检查日志后继续自动学习。")

            with col_start:
                can_start = status in ("approved", "in_progress")
                start_label = "继续自动学习" if status == "in_progress" and not is_busy else "开始自动学习"
                if st.button(start_label, type="primary",
                              disabled=is_busy or not can_start,
                              key="auto_study_btn"):
                    _run_auto_study()

            # 进度显示
            if st.session_state.curriculum_progress:
                prog = st.session_state.curriculum_progress
                p_total = prog.get("total", 0)
                p_done = prog.get("done", 0)
                if p_total > 0:
                    st.progress(p_done / p_total)
                    st.caption(
                        f"完成: {p_done}/{p_total}  |  "
                        f"进行中: {prog.get('studying', 0)}  |  "
                        f"待学: {prog.get('pending', 0)}"
                    )

            # 自动学习结果
            if st.session_state.auto_study_result:
                result = st.session_state.auto_study_result
                st.markdown("---")
                if "error" in result:
                    st.error(f"自动学习失败: {result['error']}")
                else:
                    st.success("自动学习执行完成!")
                    rc1, rc2, rc3, rc4 = st.columns(4)
                    rc1.metric("完成", result.get("completed", 0))
                    rc2.metric("失败", result.get("failed", 0))
                    rc3.metric("跳过", result.get("skipped", 0))
                    rc4.metric("总计", result.get("total", 0))

    # ==================== 标签2: 手动学习 ====================
    with tab_manual:
        st.markdown("指定URL，使用**学生智能体**收集素材：完整内容抓取、图片下载解读、代码提取、引用追踪。")

        # ---- 模式选择 ----
        study_mode = st.selectbox("学习模式", [
            "study-course — 在线课程（批量章节抓取）",
            "study-wechat — 微信文章（含引用追踪）",
            "study-github — GitHub 仓库（深度源码分析）",
            "study-arxiv — ArXiv 论文（PDF结构化分析）",
            "study-topic — 按主题自动搜索学习",
        ])
        mode_key = study_mode.split(" — ")[0]

        # ---- 输入 ----
        if mode_key == "study-topic":
            topic_input = st.text_input(
                "学习主题", placeholder="例如：RAG、LoRA微调、LLM推理优化...",
                disabled=is_busy, key="study_topic_input"
            )
            url = None
            max_pages = 50
        else:
            topic_input = None
            url = st.text_input(
                "目标 URL", placeholder="https://...", disabled=is_busy,
                key="study_url"
            )
            max_pages = 50
            if mode_key == "study-course":
                max_pages = st.slider("最大页面数", 5, 200, 50)
            if url:
                link_type = _detect_url_type(url)
                st.caption(f"检测到链接类型: **{link_type}**")

        # ---- 执行 ----
        can_run = (mode_key == "study-topic" and topic_input) or \
                  (mode_key != "study-topic" and url)
        if st.button("开始学习", type="primary", disabled=is_busy or not can_run,
                      key="manual_study_btn"):
            if mode_key == "study-topic":
                _run_study_topic(topic_input)
            else:
                _run_study_task(mode_key, url, max_pages)

        # ---- 结果 ----
        if st.session_state.study_result:
            result = st.session_state.study_result
            st.markdown("---")
            if "error" in result:
                st.error(f"学习失败: {result['error']}")
            else:
                render_status_chip("学习完成", "success")
                st.markdown(f"### {result.get('title', '')}")
                metrics = []
                if "material_ids" in result:
                    metrics.append(("收集素材数", len(result["material_ids"])))
                if "ref_materials" in result:
                    metrics.append(("引用追踪素材", len(result["ref_materials"])))
                if result.get("parent_id"):
                    metrics.append(("父素材", result.get("parent_id")))
                if metrics:
                    render_metric_cards(metrics)
                if "material_id" in result:
                    render_inline_note(f"素材 ID：{result['material_id']}")

    # ---- 底部: 素材库统计 ----
    st.markdown("---")
    store = _get_material_store()
    total = store.count()
    st.caption(f"当前素材库: {total} 条素材")


def _load_existing_curriculum():
    """尝试加载已有的课程表"""
    try:
        from src.student.curriculum_agent import CurriculumAgent
        ca = CurriculumAgent()
        return ca.load()
    except Exception:
        return None


def _run_generate_curriculum(goal: str, depth: str):
    """生成课程表"""
    from src.student.curriculum_agent import CurriculumAgent

    st.session_state.is_processing = True
    st.session_state.curriculum_error = None

    try:
        ca = CurriculumAgent()
        curriculum = ca.generate(goal=goal, depth=depth)
        st.session_state.curriculum = curriculum
        st.session_state.curriculum_error = None

    except Exception as e:
        st.session_state.curriculum_error = str(e)
        logger.error(f"课程表生成失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


def _approve_curriculum():
    """批准课程表"""
    try:
        from src.student.curriculum_agent import CurriculumAgent
        ca = CurriculumAgent()
        ca.approve()
        # 重新加载
        st.session_state.curriculum = ca.load()
    except Exception as e:
        st.error(f"批准失败: {e}")
        logger.error(f"课程表批准失败: {e}")
    st.rerun()


def _run_auto_study():
    """执行自动学习"""
    from src.student.student_agent import StudentAgent
    from src.student.curriculum_agent import CurriculumAgent

    st.session_state.is_processing = True
    st.session_state.auto_study_result = None

    try:
        student = StudentAgent()
        result = run_async(student.study_curriculum())
        st.session_state.auto_study_result = result

        # 刷新课程表和进度
        ca = CurriculumAgent()
        st.session_state.curriculum = ca.load()
        st.session_state.curriculum_progress = ca.get_progress()

    except Exception as e:
        st.session_state.auto_study_result = {"error": str(e)}
        logger.error(f"自动学习失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


def _run_study_topic(topic: str):
    """按主题自动搜索学习"""
    from src.student.student_agent import StudentAgent

    st.session_state.is_processing = True
    st.session_state.study_result = None

    try:
        student = StudentAgent()
        result = run_async(student.study_topic(topic))
        st.session_state.study_result = result

    except Exception as e:
        st.session_state.study_result = {"error": str(e)}
        logger.error(f"主题学习失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


def _run_study_task(mode_key: str, url: str, max_pages: int = 50):
    """执行学习任务"""
    from src.student.student_agent import StudentAgent

    st.session_state.is_processing = True
    st.session_state.study_result = None

    try:
        student = StudentAgent()

        if mode_key == "study-course":
            coro = student.study_course(url, max_pages=max_pages)
        elif mode_key == "study-wechat":
            coro = student.study_wechat(url)
        elif mode_key == "study-github":
            coro = student.study_github(url)
        elif mode_key == "study-arxiv":
            coro = student.study_arxiv(url)
        else:
            st.session_state.study_result = {"error": f"未知模式: {mode_key}"}
            return

        result = run_async(coro)
        st.session_state.study_result = result

    except Exception as e:
        st.session_state.study_result = {"error": str(e)}
        logger.error(f"学习任务失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


# ==================== 出版任务 ====================
def page_publish_tasks():
    render_page_hero(
        "📕 出版任务",
        "从素材检索、目录规划到章节生成和质量审核，整条出版链路都在这里完成并可直接预览效果。",
        kicker="出版社智能体",
    )

    is_busy = st.session_state.is_processing

    st.markdown("使用新的**出版社智能体**系统：从素材库检索 → 目录规划 → 逐章深度撰写 → 质量审核 → 组装输出。")

    # ---- 参数输入 ----
    topic = st.text_input("出版主题", placeholder="例如：LLM课程、Transformer详解...",
                          disabled=is_busy, key="pub_topic")

    # 高级选项
    with st.expander("高级选项"):
        parent_id = st.text_input(
            "限定父素材 ID（可选）",
            placeholder="留空则搜索全部素材",
            disabled=is_busy,
            key="pub_parent_id"
        )
        tag_input = st.text_input(
            "限定标签（可选，逗号分隔）",
            placeholder="例如：大语言模型,Transformer",
            disabled=is_busy,
            key="pub_tags"
        )

    # ---- 素材库预览 ----
    store = _get_material_store()
    total = store.count()
    render_metric_cards([("当前素材库", total)])

    if total > 0 and topic:
        preview = store.query(keyword=topic, limit=10)
        if preview:
            with st.expander(f"相关素材预览（找到 {len(preview)} 条）"):
                for m in preview:
                    st.text(f"[{m.source_type}] {m.title or '(无标题)'} (id={m.id})")
        else:
            st.caption("未找到与该主题直接匹配的素材（出版时会扩大搜索范围）")

    # ---- 执行按钮 ----
    if st.button("开始出版", type="primary", disabled=is_busy or not topic):
        tags = [t.strip() for t in tag_input.split(",") if t.strip()] if tag_input else None
        _run_publish_task(topic, parent_id or None, tags)

    # ---- 端到端模式 ----
    st.markdown("---")
    st.subheader("端到端模式（学习 + 出版）")
    st.markdown("先用学生智能体收集素材，再用出版社智能体生成知识库。")

    full_url = st.text_input("目标 URL", placeholder="https://...", disabled=is_busy,
                             key="full_url")
    full_topic = st.text_input("出版主题（可选，留空则自动检测）",
                               disabled=is_busy, key="full_topic")

    if st.button("一键执行", type="primary", disabled=is_busy or not full_url, key="full_btn"):
        _run_full_task(full_url, full_topic or None)

    # ---- 出版结果 ----
    if "publish_result" in st.session_state and st.session_state.publish_result:
        result = st.session_state.publish_result
        st.markdown("---")
        if "error" in result:
            st.error(f"出版失败: {result['error']}")
        else:
            _render_publish_result(result)


def _run_publish_task(topic: str, parent_id: str = None, tags=None):
    """执行出版任务"""
    from src.publisher_v2.publisher_agent import PublisherAgent

    st.session_state.is_processing = True
    st.session_state.publish_result = None

    try:
        publisher = PublisherAgent()
        result = run_async(
            publisher.publish_book(topic=topic, parent_id=parent_id, tags=tags)
        )
        st.session_state.publish_result = result

    except Exception as e:
        st.session_state.publish_result = {"error": str(e)}
        logger.error(f"出版任务失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


def _run_full_task(url: str, topic: str = None):
    """执行端到端任务：先学习再出版"""
    from src.student.student_agent import StudentAgent
    from src.publisher_v2.publisher_agent import PublisherAgent

    st.session_state.is_processing = True
    st.session_state.publish_result = None

    try:
        student = StudentAgent()

        # 1. 学习阶段 — 自动检测 URL 类型
        if "github.com" in url:
            study_coro = student.study_github(url)
        elif "arxiv.org" in url:
            study_coro = student.study_arxiv(url)
        elif "mp.weixin.qq.com" in url:
            study_coro = student.study_wechat(url)
        elif any(kw in url.lower() for kw in ("learn", "course", "tutorial")):
            study_coro = student.study_course(url)
        else:
            study_coro = student.study_wechat(url)

        study_result = run_async(study_coro)

        if "error" in study_result:
            st.session_state.publish_result = {"error": f"学习阶段失败: {study_result['error']}"}
            return

        # 2. 出版阶段
        pub_topic = topic or study_result.get("title", "知识库")
        pub_parent = study_result.get("parent_id", study_result.get("material_id", ""))

        publisher = PublisherAgent()
        pub_result = run_async(
            publisher.publish_book(topic=pub_topic, parent_id=pub_parent or None)
        )
        st.session_state.publish_result = pub_result

    except Exception as e:
        st.session_state.publish_result = {"error": str(e)}
        logger.error(f"端到端任务失败: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()


# ==================== 任务中心（统一任务管理） ====================
def page_task_center():
    render_page_hero(
        "🔗 任务中心",
        "统一管理待处理链接、批量学习/出版进度以及遗留流水线恢复，让整个知识生产过程可视化。",
        kicker="任务编排中枢",
    )

    is_busy = st.session_state.is_processing

    # ---- 提交新链接 ----
    st.subheader("提交新链接")
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        url = st.text_input("输入 URL", placeholder="https://mp.weixin.qq.com/s/...",
                            disabled=is_busy, label_visibility="collapsed")
    with col_btn:
        submit_clicked = st.button("提交", type="primary", disabled=is_busy)

    # 自动检测链接类型
    if url:
        link_type = _detect_url_type(url)
        st.caption(f"检测到链接类型: **{link_type}**")

    if submit_clicked:
        if not url:
            st.error("请输入 URL")
        elif not url.startswith("http"):
            st.error("请输入有效的 URL（以 http:// 或 https:// 开头）")
        else:
            TASK_MANAGER.add_url(url)
            st.success(f"已添加到待处理队列: {url}")
            st.rerun()

    st.markdown("---")

    # ---- 统计概览 ----
    data = TASK_MANAGER.load_tasks()
    pending = data.get("pending_urls", [])
    processed = data.get("processed_urls", [])

    render_metric_cards([
        ("待处理", len(pending)),
        ("已处理", len(processed)),
    ])

    st.markdown("---")

    # ---- 待处理列表 + 一键处理（新系统） ----
    st.subheader("待处理列表")
    if pending:
        for u in pending:
            link_type = _detect_url_type(u)
            st.text(f"⏳ [{link_type}] {u}")

        col_new, col_pub = st.columns(2)
        with col_new:
            if st.button("🚀 一键学习所有待处理链接", type="primary", disabled=is_busy):
                _process_pending_new_system(pending, publish=False)
        with col_pub:
            if st.button("📕 一键学习 + 出版", disabled=is_busy):
                _process_pending_new_system(pending, publish=True)
    else:
        st.info("队列为空，无待处理链接")

    st.markdown("---")

    if st.session_state.publish_result:
        st.subheader("最近一次出版结果")
        _render_publish_result(st.session_state.publish_result)
        st.markdown("---")

    # ---- 处理进度 ----
    if st.session_state.process_log:
        st.subheader("处理进度")

        total_logs = len(st.session_state.process_log)
        completed_count = sum(1 for log in st.session_state.process_log if log["status"] in ("success", "partial", "error"))

        if total_logs > 0:
            progress_value = completed_count / total_logs
            st.progress(progress_value)

            current_item = None
            for log in st.session_state.process_log:
                if log["status"] == "processing":
                    current_item = log["url"]
                    break

            if current_item:
                st.caption(f"正在处理: {current_item}")

        for log in st.session_state.process_log:
            if log["status"] == "success":
                render_list_item(f"✅ {log['url']}", log['message'])
            elif log["status"] == "partial":
                render_list_item(f"⚠️ {log['url']}", log['message'])
            elif log["status"] == "error":
                render_list_item(f"❌ {log['url']}", log['message'])
            elif log["status"] == "processing":
                render_list_item(f"⏳ {log['url']}", "处理中...")
            else:
                render_list_item(f"🔘 {log['url']}")

    st.markdown("---")

    # ---- 已处理列表 ----
    st.subheader("已处理列表")
    if processed:
        for u in processed:
            render_list_item(f"✅ {u}")
    else:
        st.info("暂无已处理链接")

    # ---- 遗留 pipeline 管理（折叠） ----
    pipeline = _get_pipeline()
    if pipeline is not None:
        try:
            from src.graph.pipeline import STEP_NAMES, STEP_DISPLAY_NAMES
            all_pipelines = pipeline.list_pipelines()
            resumable = [p for p in all_pipelines if p.status in ("paused", "running", "error")]

            if resumable:
                with st.expander("⚙️ 遗留 Pipeline 任务（旧系统）"):
                    st.caption("以下任务使用旧版 KnowledgePipeline 系统创建，可在此恢复或删除。")
                    for p in resumable:
                        step_idx = p.current_step
                        step_display = STEP_DISPLAY_NAMES[step_idx] if step_idx < len(STEP_DISPLAY_NAMES) else "已完成"
                        status_icon = {"paused": "⏸", "error": "❌", "running": "🔄"}.get(p.status, "🔘")

                        col_info, col_action = st.columns([4, 1])
                        with col_info:
                            st.text(f"{status_icon} {p.source}")
                            st.caption(f"状态: {p.status} | 步骤 {step_idx}/{len(STEP_NAMES)}: {step_display}")
                            if p.error_message:
                                st.caption(f"错误: {p.error_message}")
                        with col_action:
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                if st.button("▶ 继续", key=f"resume_{p.thread_id}", disabled=is_busy):
                                    _resume_pipeline(p.thread_id)
                            with btn_col2:
                                if st.button("🗑", key=f"delete_{p.thread_id}", disabled=is_busy):
                                    pipeline.delete_pipeline(p.thread_id)
                                    st.rerun()
        except Exception as e:
            logger.warning(f"遗留 pipeline 检查失败: {e}")


def _process_pending_new_system(pending_urls, publish=False):
    """使用新系统（StudentAgent + 可选 PublisherAgent）处理所有待处理链接"""
    from src.student.student_agent import StudentAgent

    st.session_state.is_processing = True
    st.session_state.publish_result = None
    st.session_state.process_log = [
        {"url": u, "status": "pending", "message": ""} for u in pending_urls
    ]

    try:
        student = StudentAgent()

        for i, url in enumerate(pending_urls):
            st.session_state.process_log[i]["status"] = "processing"

            try:
                # 自动检测 URL 类型并学习
                if "github.com" in url:
                    study_coro = student.study_github(url)
                elif "arxiv.org" in url:
                    study_coro = student.study_arxiv(url)
                elif "mp.weixin.qq.com" in url:
                    study_coro = student.study_wechat(url)
                elif any(kw in url.lower() for kw in ("learn", "course", "tutorial")):
                    study_coro = student.study_course(url)
                else:
                    study_coro = student.study_wechat(url)

                study_result = run_async(study_coro)

                if "error" in study_result:
                    st.session_state.process_log[i]["status"] = "error"
                    st.session_state.process_log[i]["message"] = study_result["error"]
                    continue

                msg = f"学习完成: {study_result.get('title', '')}"

                # 可选出版
                if publish:
                    try:
                        from src.publisher_v2.publisher_agent import PublisherAgent
                        pub_topic = study_result.get("title", "知识库")
                        pub_parent = study_result.get("parent_id", study_result.get("material_id", ""))
                        publisher = PublisherAgent()
                        pub_result = run_async(
                            publisher.publish_book(topic=pub_topic, parent_id=pub_parent or None)
                        )
                        st.session_state.publish_result = pub_result
                        if "error" not in pub_result:
                            pub_status = pub_result.get("status", "success")
                            msg += f" → 出版{pub_status}: {pub_result.get('output_dir', '')}"
                        else:
                            msg += f" → 出版失败: {pub_result['error']}"
                    except Exception as e:
                        msg += f" → 出版失败: {e}"

                TASK_MANAGER.mark_as_processed(url)
                final_status = "success"
                if publish and st.session_state.publish_result:
                    final_status = st.session_state.publish_result.get("status", "success")
                    if final_status not in ("success", "partial"):
                        final_status = "error"
                st.session_state.process_log[i]["status"] = final_status
                st.session_state.process_log[i]["message"] = msg

            except Exception as e:
                st.session_state.process_log[i]["status"] = "error"
                st.session_state.process_log[i]["message"] = str(e)
                logger.error(f"处理失败 {url}: {e}")

    finally:
        st.session_state.is_processing = False
        st.rerun()


def _detect_url_type(url: str) -> str:
    """自动检测 URL 类型"""
    if "mp.weixin.qq.com" in url:
        return "微信公众号"
    elif "arxiv.org" in url:
        return "ArXiv 论文"
    elif "github.com" in url:
        return "GitHub 仓库"
    elif any(kw in url.lower() for kw in ["learn", "course", "tutorial"]):
        return "在线课程"
    elif any(kw in url for kw in ["docs.", "documentation", "readthedocs"]):
        return "技术文档"
    else:
        return "通用网页"


@st.cache_resource
def _get_pipeline():
    """缓存 KnowledgePipeline 实例（含 EditorAgent），避免重复初始化。
    如果遗留 pipeline 依赖不可用则返回 None。"""
    try:
        from src.graph.pipeline import KnowledgePipeline
        from src.agents.editor_agent import EditorAgent
        editor = EditorAgent()
        run_async(editor.initialize())
        pipeline = KnowledgePipeline(editor)
        return pipeline
    except Exception as e:
        logger.warning(f"遗留 pipeline 不可用: {e}")
        return None


def _get_material_store() -> MaterialStore:
    """获取 MaterialStore 实例"""
    return MaterialStore(MATERIAL_DIR)


def _fetch_content_for_url(url: str) -> tuple:
    """
    根据 URL 类型使用对应的 researcher 获取内容。
    返回 (content, title)。
    """
    from src.researchers.wechat_reader import WechatReader
    from src.researchers.doc_researcher import DocResearcher
    from src.researchers.arxiv_researcher import ArxivResearcher

    if "mp.weixin.qq.com" in url:
        reader = WechatReader()
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
        arxiv_researcher = ArxivResearcher()
        arxiv_id = url.rstrip("/").split("/")[-1]
        papers = arxiv_researcher.search_papers(arxiv_id, max_results=1)
        if papers:
            paper = papers[0]
            content = arxiv_researcher.download_and_parse(paper['pdf_url'], paper['title'])
            if not content:
                content = paper['summary']
            return content, paper['title']
        raise Exception(f"未找到 ArXiv 论文: {arxiv_id}")

    elif _detect_url_type(url) == "在线课程":
        doc_researcher = DocResearcher()
        doc_data = doc_researcher.research_course(url, max_depth=3, max_pages=50)
        full_content = f"课程根地址: {doc_data['root_url']}\n\n"
        for page in doc_data['pages']:
            full_content += f"## 第 {page['order']+1} 章: {page['title']}\n"
            full_content += f"URL: {page['url']}\n\n{page['content']}\n\n---\n\n"
        title = doc_researcher.browser.extract_title(
            doc_researcher.browser.fetch_page(url) or ""
        ) or "在线课程"
        return full_content, title

    else:
        doc_researcher = DocResearcher()
        html = doc_researcher.browser.fetch_page(url)
        if html:
            text = doc_researcher.browser.extract_text(html)
            title = doc_researcher.browser.extract_title(html)
            return text, title or "网页文章"
        raise Exception(f"无法获取页面内容: {url}")


def _process_all_pending(pending_urls):
    """处理所有待处理链接，使用流水线 + SQLite 检查点"""
    try:
        from src.graph.pipeline import KnowledgePipeline, STEP_NAMES, STEP_DISPLAY_NAMES
    except ImportError:
        st.error("遗留 pipeline 模块不可用，请使用「学习任务」+「出版任务」代替。")
        return

    st.session_state.is_processing = True
    st.session_state.process_log = [
        {"url": u, "status": "pending", "message": ""} for u in pending_urls
    ]

    pipeline = _get_pipeline()
    if pipeline is None:
        st.error("遗留 pipeline 初始化失败，请使用「学习任务」+「出版任务」代替。")
        st.session_state.is_processing = False
        return
    pipeline.clear_pause()

    try:
        for i, url in enumerate(pending_urls):
            # 检查暂停标志
            if pipeline.is_paused():
                st.session_state.process_log[i]["status"] = "paused"
                st.session_state.process_log[i]["message"] = "已暂停（队列级别）"
                break

            st.session_state.process_log[i]["status"] = "processing"

            try:
                # 检查是否有已存在的检查点（恢复场景）
                thread_id = KnowledgePipeline.make_thread_id(url)
                existing = pipeline.get_status(thread_id)

                if existing and existing.status in ("paused", "error"):
                    # 恢复：内容已保存在检查点中
                    content = existing.content
                    title = existing.topic
                    logger.info(f"恢复已有检查点: {url} (step {existing.current_step})")
                else:
                    # 新任务：获取内容
                    content, title = _fetch_content_for_url(url)

                # 执行流水线
                result = run_async(
                    pipeline.process(content, url, title)
                )

                if result.status == "completed":
                    TASK_MANAGER.mark_as_processed(url)
                    st.session_state.process_log[i]["status"] = "success"
                    st.session_state.process_log[i]["message"] = f"已完成 -> {result.output_path}"
                elif result.status == "paused":
                    step = result.current_step
                    step_name = STEP_DISPLAY_NAMES[step] if step < len(STEP_DISPLAY_NAMES) else ""
                    st.session_state.process_log[i]["status"] = "paused"
                    st.session_state.process_log[i]["message"] = f"已暂停于 步骤{step}/{len(STEP_NAMES)}: {step_name}"
                    break
                elif result.status == "error":
                    st.session_state.process_log[i]["status"] = "error"
                    st.session_state.process_log[i]["message"] = result.error_message

            except Exception as e:
                st.session_state.process_log[i]["status"] = "error"
                st.session_state.process_log[i]["message"] = str(e)
                logger.error(f"处理失败 {url}: {e}")

    finally:
        st.session_state.is_processing = False
        st.rerun()


def _resume_pipeline(thread_id: str):
    """恢复一个已暂停/出错的流水线任务"""
    try:
        from src.graph.pipeline import STEP_NAMES, STEP_DISPLAY_NAMES
    except ImportError:
        st.error("遗留 pipeline 模块不可用")
        return

    pipeline = _get_pipeline()
    if pipeline is None:
        st.error("遗留 pipeline 初始化失败")
        return
    state = pipeline.get_status(thread_id)
    if not state:
        st.error("未找到该任务的检查点")
        return

    st.session_state.is_processing = True
    step_idx = state.current_step
    step_name = STEP_DISPLAY_NAMES[step_idx] if step_idx < len(STEP_DISPLAY_NAMES) else ""
    st.session_state.process_log = [
        {"url": state.source, "status": "processing",
         "message": f"恢复中... 步骤{step_idx}/{len(STEP_NAMES)}: {step_name}"}
    ]

    try:
        pipeline.clear_pause()
        result = run_async(
            pipeline.process(state.content, state.source, state.topic)
        )

        if result.status == "completed":
            TASK_MANAGER.mark_as_processed(state.source)
            st.session_state.process_log[0]["status"] = "success"
            st.session_state.process_log[0]["message"] = f"已完成 -> {result.output_path}"
        elif result.status == "paused":
            step = result.current_step
            step_name = STEP_DISPLAY_NAMES[step] if step < len(STEP_DISPLAY_NAMES) else ""
            st.session_state.process_log[0]["status"] = "paused"
            st.session_state.process_log[0]["message"] = f"已暂停于 步骤{step}/{len(STEP_NAMES)}: {step_name}"
        elif result.status == "error":
            st.session_state.process_log[0]["status"] = "error"
            st.session_state.process_log[0]["message"] = result.error_message
    except Exception as e:
        st.session_state.process_log[0]["status"] = "error"
        st.session_state.process_log[0]["message"] = str(e)
        logger.error(f"恢复任务失败 {state.source}: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()



# ==================== 系统设置 ====================
def page_settings():
    render_page_hero(
        "⚙️ 系统设置",
        "管理模型方案、API Key、出版参数和系统运行状态。当前已支持 DashScope / Qwen 文本优先接入。",
        kicker="系统配置",
    )

    SETTINGS_PATH = "config/settings.yaml"
    settings = {}

    # ---- 配置文件编辑 ----
    st.subheader("配置文件")

    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings_content = f.read()

        import yaml
        try:
            settings = yaml.safe_load(settings_content)
        except Exception:
            settings = {}

        # ========== 可编辑配置表单 ==========
        if settings:
            llm_cfg = settings.get("llm", {})
            models_cfg = settings.get("models", {})
            student_cfg = settings.get("student", {})
            publisher_cfg = settings.get("publisher", {})
            anthropic_cfg = llm_cfg.get("anthropic", {})
            preset_map = list_presets()
            current_preset = detect_preset(settings)

            with st.form("settings_form"):
                st.markdown("**LLM 配置**")
                preset_name = st.selectbox(
                    "LLM 方案模板",
                    options=list(preset_map.keys()),
                    index=list(preset_map.keys()).index(current_preset) if current_preset in preset_map else 0,
                    format_func=lambda key: preset_map[key]["label"],
                    key="cfg_preset",
                    help="推荐直接选模板再保存。DashScope/Qwen 模板会自动填入 base_url、API 模式、推荐模型与环境变量名。",
                )
                selected_preset = preset_map[preset_name]
                preset_notes = selected_preset.get("notes", [])
                if preset_notes:
                    st.info("\n".join(f"- {note}" for note in preset_notes))

                current_provider = llm_cfg.get("provider", selected_preset["llm"].get("provider", "openai"))
                default_api_mode = llm_cfg.get(
                    "api_mode",
                    selected_preset["llm"].get(
                        "api_mode",
                        "responses" if current_provider == "openai" else "anthropic_messages",
                    ),
                )
                default_api_env = llm_cfg.get(
                    "api_key_env",
                    selected_preset["llm"].get(
                        "api_key_env",
                        "OPENAI_API_KEY" if current_provider == "openai" else "ANTHROPIC_API_KEY",
                    ),
                )

                col1, col2 = st.columns(2)
                provider = col1.selectbox(
                    "Provider",
                    options=["openai", "anthropic"],
                    index=0 if current_provider == "openai" else 1,
                    key="cfg_provider",
                    help="openai = OpenAI 兼容接口; anthropic = Claude 原生 Messages API",
                )
                enable_thinking = col2.checkbox(
                    "启用思考模式",
                    value=llm_cfg.get("enable_thinking", selected_preset["llm"].get("enable_thinking", False)),
                    key="cfg_thinking",
                )

                col1, col2, col3, col4 = st.columns(4)
                model = col1.text_input(
                    "基础模型",
                    value=llm_cfg.get("model", selected_preset["llm"].get("model", "")),
                    key="cfg_model",
                )
                base_url = col2.text_input(
                    "Base URL",
                    value=llm_cfg.get("base_url", selected_preset["llm"].get("base_url", "")) if provider == "openai" else "",
                    key="cfg_base_url",
                    disabled=provider != "openai",
                    help="仅 openai provider 生效；anthropic provider 会忽略并移除此字段。DashScope 推荐 https://dashscope.aliyuncs.com/compatible-mode/v1 。",
                )
                api_mode_options = ["responses", "chat_completions", "auto"] if provider == "openai" else ["anthropic_messages"]
                api_mode_index = api_mode_options.index(default_api_mode) if default_api_mode in api_mode_options else 0
                api_mode = col3.selectbox(
                    "API 模式",
                    options=api_mode_options,
                    index=api_mode_index,
                    key="cfg_api_mode",
                    help="openai provider 可选 responses/chat_completions/auto；anthropic 固定 messages。DashScope/Qwen 推荐 chat_completions。",
                )
                api_key_env = col4.text_input(
                    "API Key 环境变量名",
                    value=default_api_env,
                    key="cfg_api_env",
                    help="推荐使用环境变量。DashScope 常用 DASHSCOPE_API_KEY，openai 常用 OPENAI_API_KEY，anthropic 常用 ANTHROPIC_API_KEY。",
                )
                api_key_direct = st.text_input(
                    "API Key（仅本地临时覆盖）",
                    value=llm_cfg.get("api_key", ""),
                    key="cfg_api_key",
                    type="password",
                    help="仅用于本机临时调试。若同时设置了环境变量，本地环境变量优先。DashScope 这里可直接填百炼 API Key。",
                )
                llm_max_tokens = st.number_input(
                    "默认最大输出 Tokens",
                    value=int(llm_cfg.get("max_tokens", 4096)),
                    min_value=512,
                    max_value=32768,
                    step=512,
                    key="cfg_llm_max_tokens",
                )

                # Anthropic 专用配置
                st.markdown("**Anthropic 专用配置** _(仅 provider=anthropic 时生效)_")
                col1, col2 = st.columns(2)
                thinking_budget = col1.number_input(
                    "Thinking Budget Tokens",
                    value=anthropic_cfg.get("thinking_budget_tokens", 10000),
                    min_value=1000, max_value=100000, step=1000,
                    key="cfg_thinking_budget",
                )
                anthropic_max_tokens = col2.number_input(
                    "Max Tokens",
                    value=anthropic_cfg.get("max_tokens", 8192),
                    min_value=1024, max_value=100000, step=1024,
                    key="cfg_anthropic_max",
                )

                st.markdown("**多模型配置**")
                col1, col2, col3 = st.columns(3)
                fast_model = col1.text_input(
                    "Fast 模型",
                    value=models_cfg.get("fast", selected_preset["models"].get("fast", "")),
                    key="cfg_fast",
                )
                deep_model = col2.text_input(
                    "Deep 模型",
                    value=models_cfg.get("deep", selected_preset["models"].get("deep", "")),
                    key="cfg_deep",
                )
                vision_model = col3.text_input(
                    "Vision 模型",
                    value=models_cfg.get("vision", selected_preset["models"].get("vision", "")),
                    key="cfg_vision",
                )

                st.markdown("**学生智能体**")
                col1, col2 = st.columns(2)
                s_conc = col1.number_input("并发抓取数", value=student_cfg.get("max_concurrent_fetches", 10), min_value=1, max_value=50, key="cfg_s_conc")
                s_ref = col2.number_input("引用追踪深度", value=student_cfg.get("max_reference_depth", 2), min_value=0, max_value=10, key="cfg_s_ref")

                st.markdown("**出版社智能体**")
                col1, col2, col3 = st.columns(3)
                p_min = col1.number_input("每节最少字数", value=publisher_cfg.get("min_section_words", 500), min_value=100, max_value=5000, key="cfg_p_min")
                p_max = col2.number_input("每节最多字数", value=publisher_cfg.get("max_section_words", 3000), min_value=500, max_value=10000, key="cfg_p_max")
                p_conc = col3.number_input("并行撰写数", value=publisher_cfg.get("max_concurrent_sections", 3), min_value=1, max_value=10, key="cfg_p_conc")
                col1, col2, col3 = st.columns(3)
                p_chunk = col1.number_input("素材分块字符数", value=publisher_cfg.get("writer_chunk_chars", 6000), min_value=1000, max_value=20000, step=500, key="cfg_p_chunk")
                p_overlap = col2.number_input("分块重叠字符数", value=publisher_cfg.get("writer_overlap_chars", 500), min_value=0, max_value=5000, step=100, key="cfg_p_overlap")
                p_partial_tokens = col3.number_input("单块写作 Tokens", value=publisher_cfg.get("writer_partial_max_tokens", 2200), min_value=512, max_value=8192, step=256, key="cfg_p_partial_tokens")

                submitted = st.form_submit_button("💾 保存配置", type="primary")

                if submitted:
                    settings.setdefault("llm", {})
                    settings.setdefault("models", {})
                    settings.setdefault("student", {})
                    settings.setdefault("publisher", {})

                    settings = apply_preset_to_settings(settings, preset_name)

                    # 从表单构建新配置，并避免 provider/api_mode/base_url 混搭。
                    settings["llm"]["provider"] = provider
                    settings["llm"]["model"] = model.strip() or settings["llm"].get("model", "")
                    settings["llm"]["api_mode"] = api_mode
                    settings["llm"]["api_key_env"] = api_key_env.strip() or settings["llm"].get("api_key_env", "") or (
                        "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
                    )
                    if provider == "openai":
                        settings["llm"]["base_url"] = base_url.strip() or settings["llm"].get("base_url", "")
                    else:
                        settings["llm"].pop("base_url", None)

                    if api_key_direct:
                        settings["llm"]["api_key"] = api_key_direct.strip()
                    elif "api_key" in settings["llm"]:
                        del settings["llm"]["api_key"]
                    settings["llm"]["enable_thinking"] = enable_thinking
                    settings["llm"]["max_tokens"] = int(llm_max_tokens)
                    settings["llm"]["anthropic"] = {
                        "thinking_budget_tokens": int(thinking_budget),
                        "max_tokens": int(anthropic_max_tokens),
                    }
                    settings["models"] = {
                        "fast": fast_model,
                        "deep": deep_model,
                        "vision": vision_model,
                    }
                    settings["student"]["max_concurrent_fetches"] = int(s_conc)
                    settings["student"]["max_reference_depth"] = int(s_ref)
                    settings["publisher"]["min_section_words"] = int(p_min)
                    settings["publisher"]["max_section_words"] = int(p_max)
                    settings["publisher"]["max_concurrent_sections"] = int(p_conc)
                    settings["publisher"]["writer_chunk_chars"] = int(p_chunk)
                    settings["publisher"]["writer_overlap_chars"] = int(p_overlap)
                    settings["publisher"]["writer_partial_max_tokens"] = int(p_partial_tokens)

                    try:
                        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                        st.success("✅ 配置已保存！")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"保存失败: {e}")

        # 原始 YAML 编辑器（保留，供高级用户使用）
        st.markdown("---")
        with st.expander("高级：编辑原始 YAML"):
            # 重新读取（可能刚被表单保存过）
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                current_yaml = f.read()
            edited = st.text_area("settings.yaml", value=current_yaml, height=400, key="yaml_editor")

            if st.button("保存原始 YAML"):
                try:
                    yaml.safe_load(edited)
                    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                        f.write(edited)
                    st.success("配置已保存！")
                    st.cache_resource.clear()
                except yaml.YAMLError as e:
                    st.error(f"YAML 语法错误，未保存: {e}")
    else:
        st.warning(f"配置文件 `{SETTINGS_PATH}` 不存在")

    st.markdown("---")

    # ---- API 连通性 ----
    st.subheader("API 连通性")
    llm_settings = settings.get("llm", {}) if settings else {}

    # 检查直接填写的 api_key
    direct_key = llm_settings.get("api_key", "")
    active_provider = llm_settings.get("provider", "openai")
    expected_env = llm_settings.get(
        "api_key_env",
        "OPENAI_API_KEY" if active_provider == "openai" else "ANTHROPIC_API_KEY",
    )
    if direct_key:
        masked = direct_key[:4] + "..." + direct_key[-4:] if len(direct_key) > 8 else "***"
        st.warning(f"检测到 settings.yaml 中存在直接配置的 API Key ({masked})，建议改用环境变量。")
    else:
        env_val = os.environ.get(expected_env, "")
        if env_val:
            masked = env_val[:4] + "..." + env_val[-4:] if len(env_val) > 8 else "***"
            st.success(f"✅ 环境变量 `{expected_env}` 已设置 ({masked})")
        else:
            st.error(f"❌ 未找到 API Key（当前 provider={active_provider}，环境变量 `{expected_env}` 未设置）")

    # 检查其他常用环境变量
    for env_var in ["DASHSCOPE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        val = os.environ.get(env_var, "")
        if val:
            st.caption(f"✅ `{env_var}` 已设置")

    st.markdown("---")

    # ---- 系统信息 ----
    st.subheader("系统信息")
    import sys
    import platform

    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Python: {sys.version.split()[0]}")
        st.text(f"平台: {platform.system()} {platform.release()}")
        st.text(f"Streamlit: {st.__version__}")
    with col2:
        # 检查关键包
        for pkg_name in ["openai", "yaml", "nest_asyncio", "httpx"]:
            try:
                pkg = __import__(pkg_name)
                ver = getattr(pkg, "__version__", "installed")
                st.text(f"{pkg_name}: {ver}")
            except ImportError:
                st.text(f"{pkg_name}: ❌ 未安装")


# ==================== 运行日志 ====================
def page_logs():
    render_page_hero(
        "📝 运行日志",
        "查看系统处理过程、错误和关键信息输出，便于定位学习或出版链路中的问题。",
        kicker="运行观测",
    )

    if not os.path.exists(LOG_DIR):
        st.info("暂无日志文件")
        return

    # 获取日志文件列表
    log_files = sorted(glob.glob(os.path.join(LOG_DIR, "*.log")), reverse=True)

    if not log_files:
        st.info("暂无日志文件")
        return

    # 选择日志文件
    file_names = [os.path.basename(f) for f in log_files]
    selected_log = st.selectbox("选择日志日期", file_names)

    if selected_log:
        log_path = os.path.join(LOG_DIR, selected_log)

        # 自动刷新
        auto_refresh = st.checkbox("自动刷新（每 5 秒）", value=False)
        if auto_refresh:
            st.empty()
            import time
            time.sleep(0)  # placeholder, actual refresh via rerun
            st.rerun()

        # 读取并显示日志
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        # 最新日志在上方
        lines = log_content.strip().split("\n")
        lines.reverse()

        # 日志过滤
        filter_level = st.selectbox("日志级别过滤", ["全部", "INFO", "WARNING", "ERROR"])

        if filter_level != "全部":
            lines = [l for l in lines if filter_level in l]

        st.text_area("日志内容", "\n".join(lines), height=500)
        st.caption(f"共 {len(lines)} 条日志记录")


if __name__ == "__main__":
    main()
