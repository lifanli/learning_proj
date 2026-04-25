from src.publisher_v2.publisher_agent import PublisherAgent
from src.publisher_v2.workers.cross_referencer import CrossReferencer
from src.core.worker import WorkerInput


def test_combine_materials_includes_provenance_headers_and_references():
    materials = [
        {
            "id": "m1",
            "title": "Attention Is All You Need",
            "content": "Transformer replaces recurrence with attention.",
            "source_type": "arxiv",
            "source_url": "https://arxiv.org/abs/1706.03762",
            "references": [
                {
                    "title": "Original paper PDF",
                    "type": "pdf",
                    "url": "https://arxiv.org/pdf/1706.03762.pdf",
                }
            ],
        }
    ]

    combined = PublisherAgent._combine_materials(materials)

    assert "来源类型: arxiv" in combined
    assert "来源链接: https://arxiv.org/abs/1706.03762" in combined
    assert "参考引用:" in combined
    assert "Original paper PDF" in combined


def test_cross_referencer_appends_structured_sources_and_readings():
    worker = CrossReferencer()
    content = "## Transformer\n\nTransformer 使用注意力机制。"

    output = worker.execute(
        WorkerInput(
            content=content,
            metadata={"section_title": "Transformer"},
            extra={
                "all_sections": [],
                "source_materials": [
                    {
                        "title": "Attention Is All You Need",
                        "source_type": "arxiv",
                        "source_url": "https://arxiv.org/abs/1706.03762",
                        "references": [
                            {
                                "title": "Annotated Transformer",
                                "type": "blog",
                                "url": "https://nlp.seas.harvard.edu/2018/04/03/attention.html",
                            }
                        ],
                    }
                ],
            },
        )
    )

    assert output.success is True
    assert "_来源提示：" in output.content
    assert "Attention Is All You Need" in output.content
    assert "来源与延伸阅读" in output.content
    assert "arxiv" in output.content
    assert "Annotated Transformer" in output.content
