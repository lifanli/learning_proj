"""
素材库 (MaterialStore)
======================
SQLite 索引 + 文件系统存储。大内容存文件（不截断），SQLite 做快速检索。

存储布局:
  data/materials/
    <material_id>/
      content.md          # 主体文本
      images/             # 下载的图片
      code/               # 代码片段
      meta.json           # 元数据副本
"""

import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from src.utils.logger import logger


@dataclass
class Material:
    """一条素材记录"""
    id: str = ""
    source_url: str = ""
    source_type: str = ""          # wechat, arxiv, github, course_page, doc_page, web
    content_hash: str = ""
    title: str = ""
    content: str = ""              # 主体文本（完整，不截断）
    summary: str = ""
    language: str = ""             # zh / en / mixed
    tags: List[str] = field(default_factory=list)
    parent_id: str = ""            # 所属课程/文档的父素材ID
    order_index: int = 0           # 在父素材中的顺序
    images: List[Dict[str, str]] = field(default_factory=list)  # [{url, local_path, description}]
    code_blocks: List[Dict[str, str]] = field(default_factory=list)  # [{language, code, comment}]
    references: List[Dict[str, str]] = field(default_factory=list)  # [{url, type, title}]
    terms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        # Handle JSON-serialized list/dict fields from DB
        for key in ("tags", "images", "code_blocks", "references", "terms", "metadata"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = [] if key != "metadata" else {}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class MaterialStore:
    """素材库：SQLite索引 + 文件系统存储"""

    DB_NAME = "materials.db"

    def __init__(self, base_dir: str = "data/materials"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.db_path = os.path.join(base_dir, self.DB_NAME)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY,
                    source_url TEXT,
                    source_type TEXT,
                    content_hash TEXT,
                    title TEXT,
                    summary TEXT,
                    language TEXT,
                    tags TEXT,          -- JSON array
                    parent_id TEXT,
                    order_index INTEGER DEFAULT 0,
                    images TEXT,        -- JSON array
                    code_blocks TEXT,   -- JSON array
                    references_ TEXT,   -- JSON array (references is reserved)
                    terms TEXT,         -- JSON array
                    metadata TEXT,      -- JSON object
                    created_at REAL,
                    updated_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_url ON materials(source_url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON materials(source_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON materials(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON materials(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON materials(tags)")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def exists_by_hash(self, content_hash: str) -> bool:
        """检查内容是否已存在（去重）"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM materials WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return row is not None

    def exists_by_url(self, source_url: str) -> Optional[str]:
        """按URL检查是否已存在，返回material_id或None"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM materials WHERE source_url = ?", (source_url,)
            ).fetchone()
            return row["id"] if row else None

    def save(self, material: Material) -> str:
        """保存素材，返回material_id。自动去重（基于content_hash）。"""
        now = time.time()

        if not material.id:
            material.id = uuid.uuid4().hex[:12]
        if not material.content_hash and material.content:
            material.content_hash = self.compute_hash(material.content)
        if not material.created_at:
            material.created_at = now
        material.updated_at = now

        # 去重检查
        if material.content_hash and self.exists_by_hash(material.content_hash):
            existing_id = self._get_id_by_hash(material.content_hash)
            if existing_id:
                logger.info(f"素材已存在（hash重复），跳过: {material.title[:50]}")
                return existing_id

        # 保存内容到文件系统（不截断）
        mat_dir = os.path.join(self.base_dir, material.id)
        os.makedirs(mat_dir, exist_ok=True)
        os.makedirs(os.path.join(mat_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(mat_dir, "code"), exist_ok=True)

        # 写主体内容
        content_path = os.path.join(mat_dir, "content.md")
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(material.content)

        # 写元数据副本
        meta_path = os.path.join(mat_dir, "meta.json")
        meta = material.to_dict()
        meta.pop("content", None)  # 不重复存储正文
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 保存代码块到独立文件
        for i, block in enumerate(material.code_blocks):
            ext = block.get("language", "txt") or "txt"
            code_path = os.path.join(mat_dir, "code", f"block_{i}.{ext}")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(block.get("code", ""))

        # 写入SQLite索引
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO materials
                (id, source_url, source_type, content_hash, title, summary, language,
                 tags, parent_id, order_index, images, code_blocks, references_, terms,
                 metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                material.id,
                material.source_url,
                material.source_type,
                material.content_hash,
                material.title,
                material.summary,
                material.language,
                json.dumps(material.tags, ensure_ascii=False),
                material.parent_id,
                material.order_index,
                json.dumps(material.images, ensure_ascii=False),
                json.dumps(material.code_blocks, ensure_ascii=False),
                json.dumps(material.references, ensure_ascii=False),
                json.dumps(material.terms, ensure_ascii=False),
                json.dumps(material.metadata, ensure_ascii=False),
                material.created_at,
                material.updated_at,
            ))

        logger.info(f"素材已保存: [{material.source_type}] {material.title[:60]} (id={material.id})")
        return material.id

    def get(self, material_id: str) -> Optional[Material]:
        """按ID获取完整素材（含文件内容）"""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
            if not row:
                return None

        d = dict(row)
        # Rename references_ back to references
        d["references"] = d.pop("references_", "[]")
        mat = Material.from_dict(d)

        # 从文件系统加载完整内容
        content_path = os.path.join(self.base_dir, material_id, "content.md")
        if os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                mat.content = f.read()

        return mat

    def query(
        self,
        source_type: str = None,
        parent_id: str = None,
        tags: List[str] = None,
        keyword: str = None,
        limit: int = 100,
    ) -> List[Material]:
        """查询素材（不加载完整content，只返回索引信息）"""
        conditions = []
        params = []

        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if parent_id:
            conditions.append("parent_id = ?")
            params.append(parent_id)
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
        if keyword:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM materials WHERE {where} ORDER BY order_index, created_at DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            d["references"] = d.pop("references_", "[]")
            mat = Material.from_dict(d)
            mat.content = ""  # 不加载正文，节省内存
            results.append(mat)

        results.sort(key=self._material_priority_key)
        return results

    def get_children(self, parent_id: str) -> List[Material]:
        """获取某父素材下的所有子素材（按order_index排序）"""
        return self.query(parent_id=parent_id, limit=500)

    def delete(self, material_id: str):
        """删除素材及其文件"""
        with self._conn() as conn:
            conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        mat_dir = os.path.join(self.base_dir, material_id)
        if os.path.exists(mat_dir):
            shutil.rmtree(mat_dir)
        logger.info(f"素材已删除: {material_id}")

    def count(self, source_type: str = None) -> int:
        """统计素材数量"""
        with self._conn() as conn:
            if source_type:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM materials WHERE source_type = ?",
                    (source_type,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM materials").fetchone()
            return row["cnt"]

    def list_all_tags(self) -> List[str]:
        """获取所有标签"""
        with self._conn() as conn:
            rows = conn.execute("SELECT DISTINCT tags FROM materials WHERE tags != '[]'").fetchall()
        all_tags = set()
        for row in rows:
            try:
                tags = json.loads(row["tags"])
                all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass
        return sorted(all_tags)

    def save_image(self, material_id: str, image_url: str, image_data: bytes, filename: str) -> str:
        """保存图片到素材目录，返回本地路径"""
        img_dir = os.path.join(self.base_dir, material_id, "images")
        os.makedirs(img_dir, exist_ok=True)
        local_path = os.path.join(img_dir, filename)
        with open(local_path, "wb") as f:
            f.write(image_data)
        return local_path

    def _get_id_by_hash(self, content_hash: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM materials WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return row["id"] if row else None

    def get_image_path(self, material_id: str) -> str:
        """获取素材的图片目录路径"""
        return os.path.join(self.base_dir, material_id, "images")

    @staticmethod
    def _material_priority_key(mat: Material):
        processing = (mat.metadata or {}).get("processing", {})
        quality = processing.get("quality", {}) if isinstance(processing, dict) else {}
        readiness = processing.get("ready_for_publish", {}) if isinstance(processing, dict) else {}
        ready = 1 if readiness.get("ready_for_publish") else 0
        score = quality.get("score", 0) if isinstance(quality, dict) else 0
        return (-ready, -score, mat.order_index, -(mat.created_at or 0.0))

    def save_batch(self, materials: List[Material]) -> List[str]:
        """批量保存素材，单事务批量写入 SQLite，减少 I/O。返回 material_id 列表。"""
        now = time.time()
        saved_ids = []

        # 预处理所有素材：生成 ID、hash、写文件
        rows_to_insert = []
        for material in materials:
            if not material.id:
                material.id = uuid.uuid4().hex[:12]
            if not material.content_hash and material.content:
                material.content_hash = self.compute_hash(material.content)
            if not material.created_at:
                material.created_at = now
            material.updated_at = now

            # 去重检查
            if material.content_hash and self.exists_by_hash(material.content_hash):
                existing_id = self._get_id_by_hash(material.content_hash)
                if existing_id:
                    saved_ids.append(existing_id)
                    continue

            # 写文件系统
            mat_dir = os.path.join(self.base_dir, material.id)
            os.makedirs(mat_dir, exist_ok=True)
            os.makedirs(os.path.join(mat_dir, "images"), exist_ok=True)
            os.makedirs(os.path.join(mat_dir, "code"), exist_ok=True)

            content_path = os.path.join(mat_dir, "content.md")
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(material.content)

            meta_path = os.path.join(mat_dir, "meta.json")
            meta = material.to_dict()
            meta.pop("content", None)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            for i, block in enumerate(material.code_blocks):
                ext = block.get("language", "txt") or "txt"
                code_path = os.path.join(mat_dir, "code", f"block_{i}.{ext}")
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(block.get("code", ""))

            rows_to_insert.append((
                material.id,
                material.source_url,
                material.source_type,
                material.content_hash,
                material.title,
                material.summary,
                material.language,
                json.dumps(material.tags, ensure_ascii=False),
                material.parent_id,
                material.order_index,
                json.dumps(material.images, ensure_ascii=False),
                json.dumps(material.code_blocks, ensure_ascii=False),
                json.dumps(material.references, ensure_ascii=False),
                json.dumps(material.terms, ensure_ascii=False),
                json.dumps(material.metadata, ensure_ascii=False),
                material.created_at,
                material.updated_at,
            ))
            saved_ids.append(material.id)

        # 单事务批量写入 SQLite
        if rows_to_insert:
            with self._conn() as conn:
                conn.executemany("""
                    INSERT OR REPLACE INTO materials
                    (id, source_url, source_type, content_hash, title, summary, language,
                     tags, parent_id, order_index, images, code_blocks, references_, terms,
                     metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_to_insert)

        logger.info(f"批量保存完成: {len(saved_ids)}条素材")
        return saved_ids
