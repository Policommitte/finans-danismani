"""Sohbet sozlesmeleri.

SSE olaylarinin sozlesmesi burada DEGIL, `docs/api-sozlesmesi.md` icindedir:
akis gövdesi bir Pydantic modeli degil, `text/event-stream` gövdesidir.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="Kullanici mesaji")
    conversation_id: int | None = Field(
        default=None,
        description="Mevcut sohbet. Bos birakilirsa yeni sohbet acilir ve "
        "`meta` olayinda id doner.",
    )


class Conversation(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int | None = None


class ConversationsResponse(BaseModel):
    items: list[Conversation]


class Message(BaseModel):
    id: int
    sender_role: str = Field(description="user | assistant")
    message_content: str
    meta: dict = Field(default_factory=dict, description="sources · agent_errors · intent")
    created_at: str


class MessagesResponse(BaseModel):
    conversation_id: int
    items: list[Message]
