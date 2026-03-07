from fastapi import APIRouter
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
    """与智能体对话"""
    return {
        "response": "这是示例响应，实际将调用 LangChain 智能体",
        "session_id": request.session_id or "session_123"
    }
