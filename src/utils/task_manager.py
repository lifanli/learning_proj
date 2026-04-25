import yaml
import os
from src.utils.logger import logger


class TaskManager:
    def __init__(self, task_file: str = "config/tasks.yaml"):
        self.task_file = task_file
        if not os.path.exists(task_file):
            self._create_default_task_file()

    def _create_default_task_file(self):
        default_data = {"pending_urls": [], "processed_urls": []}
        with open(self.task_file, "w", encoding="utf-8") as f:
            yaml.dump(default_data, f)

    def load_tasks(self) -> dict:
        with open(self.task_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"pending_urls": [], "processed_urls": []}

    def add_url(self, url: str):
        data = self.load_tasks()
        if url not in data["pending_urls"] and url not in data["processed_urls"]:
            data["pending_urls"].append(url)
            self._save_tasks(data)
            logger.info(f"已添加 URL 到待处理队列: {url}")

    def get_pending_urls(self) -> list:
        data = self.load_tasks()
        return data.get("pending_urls", [])

    def mark_as_processed(self, url: str):
        data = self.load_tasks()
        if url in data["pending_urls"]:
            data["pending_urls"].remove(url)
            if "processed_urls" not in data:
                data["processed_urls"] = []
            data["processed_urls"].append(url)
            self._save_tasks(data)
            logger.info(f"已将 URL 标记为已处理: {url}")

    def _save_tasks(self, data: dict):
        with open(self.task_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
