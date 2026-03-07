from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    与智能体对话
    
    - **message**: 用户消息
    - **session_id**: 会话 ID（可选）
    """
    # TODO: 集成 LangChain 智能体
    return {
        "response": "这是一个示例响应。实际实现将调用 LangChain 智能体。",
        "session_id": request.session_id or "session_123"
    }


@router.get("/sessions")
async def get_chat_sessions():
    """获取对话历史"""
    # TODO: 从数据库查询对话历史
    return []
