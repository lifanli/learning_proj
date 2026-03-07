"""
内置技能 - 文件操作
"""

import os
from pathlib import Path
from typing import List, Optional


def read_file(path: str, limit: Optional[int] = None) -> str:
    """读取文件内容"""
    with open(path, 'r', encoding='utf-8') as f:
        if limit:
            return f.read(limit)
        return f.read()


def write_file(path: str, content: str) -> bool:
    """写入文件"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def list_files(dir_path: str, pattern: str = "*") -> List[str]:
    """列出目录文件"""
    from glob import glob
    return glob(os.path.join(dir_path, pattern))


def file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(path)


def delete_file(path: str) -> bool:
    """删除文件"""
    if file_exists(path):
        os.remove(path)
        return True
    return False
