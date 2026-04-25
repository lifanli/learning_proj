import os
import yaml
from dotenv import load_dotenv
from typing import List, Dict, Optional, Generator, Union
from src.utils.logger import logger
from src.core.llm_client import LLMClient

# Load env
load_dotenv()

class BaseAgent:
    def __init__(self, role_name: str = "BaseAgent", role_instruction: str = ""):
        self.role_name = role_name
        self.role_instruction = role_instruction
        self.config = self._load_config()
        self.llm_client = LLMClient(self.config)
        self.model = self.config['llm']['model']
        self.translation_prompt = self.config['language']['translation_prompt']

    def _load_config(self) -> dict:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"无法加载配置文件: {e}")
            raise

    @property
    def client(self):
        """向后兼容：返回底层 SDK 客户端"""
        return self.llm_client.client

    def chat(self, user_input: str, history: List[Dict] = None, stream: bool = True) -> Union[str, Generator]:
        """
        与模型对话，支持思考过程流式输出。
        """
        if history is None:
            history = []

        # System prompt with role instruction and language enforcement
        messages = [
            {"role": "system", "content": f"{self.role_instruction}\n\nIMPORTANT: {self.translation_prompt}"}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        enable_thinking = self.config['llm'].get('enable_thinking', False)

        try:
            result = self.llm_client.chat_completion(
                messages=messages,
                model=self.model,
                stream=stream,
                enable_thinking=enable_thinking,
            )

            if stream:
                return self._handle_stream(result)
            else:
                return result

        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            return f"Error: {e}"

    def _handle_stream(self, response):
        """处理流式响应，分离思考过程和正式回复"""
        is_answering = False
        full_content = ""

        print(f"\n[{self.role_name}] 正在思考...\n" + "-" * 20)

        for content_type, text in response:
            if content_type == "thinking":
                print(text, end="", flush=True)
            elif content_type == "content":
                if not is_answering:
                    print("\n" + "-" * 20 + f"\n[{self.role_name}] 回复:\n")
                    is_answering = True
                print(text, end="", flush=True)
                full_content += text

        print("\n")
        return full_content

if __name__ == "__main__":
    # Test
    agent = BaseAgent(
        role_name="TestBot",
        role_instruction="You are a helpful assistant."
    )
    agent.chat("你好，请介绍一下你自己。")
