"""
通信模块

Worker 之间的消息传递和状态同步
"""

from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class Message:
    """消息结构"""
    sender: str
    receiver: str
    content: str
    timestamp: datetime
    type: str = "info"  # info/task/result/alert


@dataclass
class WorkerStatus:
    """Worker 状态"""
    name: str
    role: str
    current_task: str
    progress: float  # 0-100
    status: str  # idle/working/blocked/done
    last_update: datetime


class CommunicationHub:
    """通信中心"""
    
    def __init__(self):
        self.messages: List[Message] = []
        self.worker_status: Dict[str, WorkerStatus] = {}
    
    def send_message(self, sender: str, receiver: str, content: str, 
                     msg_type: str = "info"):
        """发送消息"""
        msg = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            timestamp=datetime.now(),
            type=msg_type
        )
        self.messages.append(msg)
        print(f"[{msg.timestamp.strftime('%H:%M:%S')}] "
              f"{sender} → {receiver}: {content}")
    
    def broadcast(self, sender: str, content: str, msg_type: str = "info"):
        """广播消息"""
        self.send_message(sender, "ALL", content, msg_type)
        print(f"  [广播给所有 Worker]")
    
    def update_status(self, name: str, role: str, task: str, 
                      progress: float, status: str):
        """更新 Worker 状态"""
        self.worker_status[name] = WorkerStatus(
            name=name,
            role=role,
            current_task=task,
            progress=progress,
            status=status,
            last_update=datetime.now()
        )
    
    def get_status_report(self) -> str:
        """获取状态报告"""
        report = ["📊 Worker 状态报告", "=" * 40]
        for name, status in self.worker_status.items():
            emoji = {"idle": "⏳", "working": "💻", "blocked": "🚫", "done": "✅"}
            emoji = emoji.get(status.status, "❓")
            report.append(
                f"{emoji} {name} ({status.role}): "
                f"{status.current_task} ({status.progress}%) - {status.status}"
            )
        return "\n".join(report)
    
    def get_messages(self, receiver: str = None) -> List[Message]:
        """获取消息"""
        if receiver is None or receiver == "ALL":
            return self.messages
        return [m for m in self.messages if m.receiver in [receiver, "ALL"]]
    
    def export_report(self) -> dict:
        """导出报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "workers": {
                name: {
                    "role": status.role,
                    "task": status.current_task,
                    "progress": status.progress,
                    "status": status.status
                }
                for name, status in self.worker_status.items()
            },
            "messages": [
                {
                    "sender": m.sender,
                    "receiver": m.receiver,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "type": m.type
                }
                for m in self.messages[-20:]  # 最近 20 条
            ]
        }


# 全局通信中心
hub = CommunicationHub()


def init_workers():
    """初始化 Worker 状态"""
    workers = [
        ("张建国", "Architect", "代码开发", 100, "done"),
        ("林觅", "Search", "技术调研", 50, "working"),
        ("郑思远", "Challenger", "代码审查", 0, "idle"),
        ("运维", "DevOps", "Git 管理", 100, "done"),
        ("测试员", "Tester", "测试运行", 0, "blocked"),
    ]
    for name, role, task, progress, status in workers:
        hub.update_status(name, role, task, progress, status)


def print_status():
    """打印状态"""
    print(hub.get_status_report())


if __name__ == "__main__":
    init_workers()
    print_status()
    
    # 模拟通信
    print("\n" + "=" * 40)
    hub.broadcast("Manager", "项目进度同步会议现在开始")
    hub.send_message("Architect", "Tester", "代码已完成，可以测试")
    hub.send_message("Tester", "Architect", "收到，但需要安装依赖")
    hub.send_message("Tester", "ALL", "阻塞：需要安装 flask/requests/pytest")
    
    print("\n" + "=" * 40)
    print_status()
