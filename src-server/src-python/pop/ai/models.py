"""Pydantic models for AI Advisor chat."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request to send a message to the AI advisor."""

    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    build_context: dict | None = None
    api_key: str = ""


class ChatResponse(BaseModel):
    """Response from the AI advisor."""

    message: str
    conversation_id: str = ""
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Build Generator models
# ---------------------------------------------------------------------------


class BuildPreferences(BaseModel):
    """User preferences collected during the intake conversation."""

    main_skill: str = ""
    weapon_type: str = ""
    class_name: str = ""
    ascendancy_name: str = ""
    budget_chaos: int = 0
    league: str = "Standard"
    playstyle: str = ""


class GenerateRequest(BaseModel):
    """Request to generate a full build guide from preferences."""

    api_key: str
    preferences: BuildPreferences
    history: list[ChatMessage] = Field(default_factory=list)


class RefineRequest(BaseModel):
    """Request to refine a build guide based on trade prices and budget."""

    api_key: str
    guide: dict  # Serialized BuildGuide
    trade_prices: list[dict] = Field(default_factory=list)
    budget_chaos: int = 0
    history: list[ChatMessage] = Field(default_factory=list)
    message: str = ""
