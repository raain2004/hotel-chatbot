from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="ID người dùng (Messenger PSID hoặc ID test)")
    message: str = Field(..., min_length=1, max_length=4000)
    channel: str = Field(default="web", description="messenger | zalo | web")


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    transferred_to_human: bool = False
    duplicate: bool = False
