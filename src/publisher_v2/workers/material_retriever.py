"""
素材检索Worker (MaterialRetriever)
====================================
从素材库中检索与指定章节相关的素材完整内容。
"""

from typing import List
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import MaterialStore
from src.utils.logger import logger


class MaterialRetriever(BaseWorker):
    """素材检索Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="MaterialRetriever",
            description="从素材库检索素材完整内容",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        material_ids = input_data.extra.get("material_ids", [])
        store_path = input_data.extra.get("store_path", "data/materials")

        if not material_ids:
            return WorkerOutput(success=True, data={"materials": []})

        store = MaterialStore(store_path)
        materials = []

        for mid in material_ids:
            mat = store.get(mid)
            if mat:
                materials.append({
                    "id": mat.id,
                    "title": mat.title,
                    "content": mat.content,
                    "source_type": mat.source_type,
                    "source_url": mat.source_url,
                    "images": mat.images,
                    "code_blocks": mat.code_blocks,
                    "terms": mat.terms,
                    "tags": mat.tags,
                })
            else:
                logger.warning(f"素材未找到: {mid}")

        return WorkerOutput(
            success=True,
            data={"materials": materials},
        )
