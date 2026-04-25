"""
test_book_planner.py — BookPlanner (YAML 解析 / think 标签清理 / 降级) 测试
"""

from unittest.mock import patch, MagicMock
import pytest

from src.publisher_v2.book_planner import BookPlanner, BookOutline


# ---------------------------------------------------------------------------
# _parse_outline 纯逻辑测试（无 mock，无网络）
# ---------------------------------------------------------------------------

class TestParseOutline:
    """_parse_outline YAML 解析逻辑"""

    def setup_method(self):
        self.planner = object.__new__(BookPlanner)

    def test_parse_outline_normal_yaml(self):
        """正常 YAML 带代码围栏"""
        llm_output = """```yaml
title: "测试书籍"
description: "一本测试用书"
chapters:
  - title: "第1章 基础"
    sections:
      - title: "1.1 入门"
        material_ids: ["m1", "m2"]
        description: "入门要点"
```"""
        outline = self.planner._parse_outline(llm_output)

        assert outline.title == "测试书籍"
        assert outline.description == "一本测试用书"
        assert len(outline.chapters) == 1
        assert outline.chapters[0]["title"] == "第1章 基础"
        assert outline.chapters[0]["sections"][0]["material_ids"] == ["m1", "m2"]

    def test_parse_outline_with_think_tags(self):
        """带 <think> 标签的 LLM 输出应被正确清理"""
        llm_output = """<think>
我来分析一下这些素材...
应该按照由浅入深排列...
</think>

```yaml
title: "深度学习入门"
description: "系统学习深度学习"
chapters:
  - title: "第1章 神经网络基础"
    sections:
      - title: "1.1 感知机"
        material_ids: ["m1"]
        description: "感知机原理"
```"""
        outline = self.planner._parse_outline(llm_output)

        assert outline.title == "深度学习入门"
        assert len(outline.chapters) == 1
        assert outline.chapters[0]["sections"][0]["material_ids"] == ["m1"]

    def test_parse_outline_unclosed_think(self):
        """未闭合的 <think> 标签不应导致解析失败"""
        llm_output = """```yaml
title: "有效内容"
description: "desc"
chapters:
  - title: "第1章 章节"
    sections:
      - title: "1.1 节"
        material_ids: ["m1"]
        description: "要点"
```

<think>
这是一段未闭合的思考内容..."""

        outline = self.planner._parse_outline(llm_output)

        assert outline.title == "有效内容"
        assert len(outline.chapters) == 1

    def test_parse_outline_empty_yaml_returns_unnamed(self):
        """空 YAML 返回未命名 BookOutline"""
        outline = self.planner._parse_outline("")

        assert outline.title == "未命名"
        assert outline.chapters == []

    def test_parse_outline_bare_yaml(self):
        """无代码围栏的裸 YAML"""
        llm_output = """title: "裸YAML书籍"
description: "无围栏"
chapters:
  - title: "第1章 唯一章节"
    sections:
      - title: "1.1 节"
        material_ids: ["m1"]
        description: "要点"
"""
        outline = self.planner._parse_outline(llm_output)

        assert outline.title == "裸YAML书籍"
        assert len(outline.chapters) == 1


# ---------------------------------------------------------------------------
# _plan_with_llm 降级逻辑
# ---------------------------------------------------------------------------

class TestPlanWithLlmFallback:
    """空章节时应降级到 _fallback_outline"""

    def test_plan_with_llm_fallback_on_empty_chapters(self, mock_settings):
        """当 _parse_outline 返回空 chapters 时，使用降级方案"""
        planner = BookPlanner()

        # mock llm_call 返回无效 YAML（不含 chapters）
        with patch.object(planner, "llm_call", return_value="无效内容，没有YAML"):
            summaries = [
                {"id": "m1", "summary": "素材1"},
                {"id": "m2", "summary": "素材2"},
            ]
            outline = planner._plan_with_llm("测试主题", summaries)

        # 应使用降级方案，有章节
        assert len(outline.chapters) > 0
        assert outline.title == "测试主题"
