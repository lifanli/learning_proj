from src.student.study_planner import StudyPlanner


def test_plan_web_site_reads_usable_child_pages_and_skips_login():
    planner = StudyPlanner()
    pages = {
        "https://example.com/": """
            <html><head><title>Home</title></head><body>
              <nav>Navigation only</nav>
              <a href="/docs/intro">Intro</a>
              <a href="/member/login">Login</a>
              <a href="https://other.example.com/docs/intro">External</a>
            </body></html>
        """,
        "https://example.com/docs/intro": """
            <html><head><title>Intro</title></head><body>
              <article><h1>Intro</h1><p>{}</p></article>
            </body></html>
        """.format("This is useful documentation content. " * 20),
        "https://example.com/member/login": """
            <html><head><title>Login</title></head><body>
              <main>登录 password captcha</main>
            </body></html>
        """,
    }

    planner.browser.fetch_page = lambda url: pages.get(url, "")

    plan = planner.plan_web_site(
        "https://example.com/",
        max_pages=5,
        max_depth=1,
        min_content_chars=120,
        topic="documentation",
    )

    assert [page["url"] for page in plan.pages] == ["https://example.com/docs/intro"]
    assert plan.pages[0]["title"] == "Intro"


def test_plan_web_site_can_follow_second_level_child_page():
    planner = StudyPlanner()
    pages = {
        "https://example.com/": """
            <html><head><title>Home</title></head><body>
              <a href="/docs/index">Docs</a>
            </body></html>
        """,
        "https://example.com/docs/index": """
            <html><head><title>Docs Index</title></head><body>
              <a href="/docs/deep-topic">Deep Topic</a>
            </body></html>
        """,
        "https://example.com/docs/deep-topic": """
            <html><head><title>Deep Topic</title></head><body>
              <article><p>{}</p></article>
            </body></html>
        """.format("Deep technical explanation. " * 20),
    }

    planner.browser.fetch_page = lambda url: pages.get(url, "")

    plan = planner.plan_web_site(
        "https://example.com/",
        max_pages=5,
        max_depth=2,
        min_content_chars=120,
        topic="deep topic",
    )

    assert [page["url"] for page in plan.pages] == ["https://example.com/docs/deep-topic"]
    assert plan.pages[0]["depth"] == 2


def test_plan_web_site_stays_inside_docs_product_scope():
    planner = StudyPlanner()
    pages = {
        "https://huggingface.co/docs/transformers/index": """
            <html><head><title>Transformers</title></head><body>
              <article><p>{}</p></article>
              <a href="/docs/transformers/installation">Installation</a>
              <a href="/learn/llm-course/chapter1/1">LLM Course</a>
            </body></html>
        """.format("Transformers documentation. " * 20),
        "https://huggingface.co/docs/transformers/installation": """
            <html><head><title>Installation</title></head><body>
              <article><p>{}</p></article>
            </body></html>
        """.format("Install transformers package. " * 20),
        "https://huggingface.co/learn/llm-course/chapter1/1": """
            <html><head><title>LLM Course</title></head><body>
              <article><p>{}</p></article>
            </body></html>
        """.format("This is a different product area. " * 20),
    }
    planner.browser.fetch_page = lambda url: pages.get(url, "")

    plan = planner.plan_web_site(
        "https://huggingface.co/docs/transformers/index",
        max_pages=5,
        max_depth=1,
        min_content_chars=120,
        topic="transformers",
        source_type="doc",
    )

    urls = [page["url"] for page in plan.pages]
    assert "https://huggingface.co/docs/transformers/index" in urls
    assert "https://huggingface.co/docs/transformers/installation" in urls
    assert "https://huggingface.co/learn/llm-course/chapter1/1" not in urls
