"""Shared request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: str
    content: str


class AiChatRequest(BaseModel):
    message: str
    history: list[ChatMessageIn] = Field(default_factory=list)
    build_context: dict | None = None


class GeneratorChatRequest(BaseModel):
    message: str
    history: list[ChatMessageIn] = Field(default_factory=list)


class GenerateBuildRequest(BaseModel):
    preferences: dict
    history: list[ChatMessageIn] = Field(default_factory=list)


class RefineBuildRequest(BaseModel):
    guide: dict
    trade_prices: list[dict] = Field(default_factory=list)
    budget_chaos: int = 0
    history: list[ChatMessageIn] = Field(default_factory=list)
    message: str = ""


class AiChatResponse(BaseModel):
    message: str
    tokens_used: int = 0


class DiscordTokenRequest(BaseModel):
    code: str
    redirect_uri: str = "http://localhost:8458/callback"


class TokenResponse(BaseModel):
    access_token: str
    user: UserInfo


class UserInfo(BaseModel):
    id: int
    discord_id: str
    discord_username: str
    discord_avatar: str
    subscription_status: str


class CheckoutResponse(BaseModel):
    checkout_url: str
