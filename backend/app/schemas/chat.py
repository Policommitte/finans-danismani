"""Sohbet sozlesmeleri.

SSE olaylarinin sozlesmesi burada DEGIL, `docs/api-sozlesmesi.md` icindedir:
akis gövdesi bir Pydantic modeli degil, `text/event-stream` gövdesidir.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatAttachment(BaseModel):
    """Sohbet mesajina eklenen gorsel/belge.

    `data_base64` boyut/format dogrulamasi route seviyesinde, akis
    baslamadan once yapilir (bkz. routes/chat.py) - aksi halde 422 yerine
    yarim bir SSE akisi donerdi.

    `kind` alani frontend'in dosya secici arayuzunden (goersel mi / belge mi
    tiklandi) gelir; asil tur tespiti yine de dosya adindan yapilir
    (`app.documents.parser.belge_turu`) - bu alan yalnizca UI niyetini
    tasir, sunucu tarafinda GUVENLIK KARARI icin kullanilmaz.
    """

    kind: Literal["image", "file"]
    filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    data_base64: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="Kullanici mesaji")
    conversation_id: int | None = Field(
        default=None,
        description="Mevcut sohbet. Bos birakilirsa yeni sohbet acilir ve "
        "`meta` olayinda id doner.",
    )
    attachment: ChatAttachment | None = Field(
        default=None,
        description="Opsiyonel PDF/Excel/gorsel eki - varsa `document_analysis` "
        "ajani ekli dosyayi analiz edip Turkce PDF rapor uretir.",
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
