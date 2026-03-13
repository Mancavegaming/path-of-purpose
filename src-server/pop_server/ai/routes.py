"""AI proxy routes — server-side AI calls with the hosted API key.

All endpoints require an active subscription. The Anthropic/Gemini API key
is held server-side and never exposed to the client.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends

from pop_server.auth.middleware import require_subscription
from pop_server.config import settings
from pop_server.db import log_usage
from pop_server.models import (
    AiChatRequest,
    AiChatResponse,
    GenerateBuildRequest,
    GeneratorChatRequest,
    RefineBuildRequest,
    ResolveTreeUrlsRequest,
)

# Add src-python to sys.path so we can import pop.ai modules directly
_src_python = str(Path(__file__).resolve().parent.parent.parent.parent / "src-python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from pop.ai.advisor import Advisor  # noqa: E402
from pop.ai.generator import BuildGenerator  # noqa: E402
from pop.ai.models import BuildPreferences, ChatMessage  # noqa: E402
from pop.build_parser.tree_data import resolve_guide_tree_urls  # noqa: E402

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _get_api_key() -> str:
    """Return the server-side API key for the configured provider."""
    if settings.ai_provider == "openai":
        return settings.openai_api_key
    elif settings.ai_provider == "gemini":
        return settings.gemini_api_key
    return settings.anthropic_api_key


def _to_chat_messages(raw: list) -> list[ChatMessage]:
    """Convert request history to ChatMessage objects."""
    return [ChatMessage(role=m.role, content=m.content) for m in raw]


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(req: AiChatRequest, user: dict = Depends(require_subscription)):
    """Proxy an AI advisor chat message through the server."""
    advisor = Advisor()
    history = _to_chat_messages(req.history)

    response = await advisor.chat(
        message=req.message,
        api_key=_get_api_key(),
        history=history,
        build_context=req.build_context,
        provider=settings.ai_provider,
    )

    log_usage(user["id"], "ai_chat", response.tokens_used)

    return AiChatResponse(message=response.message, tokens_used=response.tokens_used)


@router.post("/generator-chat", response_model=AiChatResponse)
async def generator_chat(
    req: GeneratorChatRequest, user: dict = Depends(require_subscription)
):
    """Proxy a build generator intake chat message."""
    gen = BuildGenerator()
    history = _to_chat_messages(req.history)

    response = await gen.chat_intake(
        message=req.message,
        api_key=_get_api_key(),
        history=history,
        provider=settings.ai_provider,
    )

    log_usage(user["id"], "generator_chat", response.tokens_used)

    return AiChatResponse(message=response.message, tokens_used=response.tokens_used)


@router.post("/generate-build")
async def generate_build(
    req: GenerateBuildRequest, user: dict = Depends(require_subscription)
):
    """Generate a full build guide from preferences."""
    gen = BuildGenerator()
    prefs = BuildPreferences(**req.preferences)
    history = _to_chat_messages(req.history)

    guide = await gen.generate(
        api_key=_get_api_key(),
        preferences=prefs,
        history=history,
        provider=settings.ai_provider,
    )

    log_usage(user["id"], "generate_build", 0)

    # Resolve passive tree URLs from key_nodes
    guide_dict = guide.model_dump(mode="json")
    try:
        guide_dict = await resolve_guide_tree_urls(guide_dict)
    except Exception:
        pass  # Non-critical — guide still works without tree URLs

    return guide_dict


@router.post("/refine-build")
async def refine_build(
    req: RefineBuildRequest, user: dict = Depends(require_subscription)
):
    """Refine a build guide based on trade prices and budget."""
    gen = BuildGenerator()
    history = _to_chat_messages(req.history)

    refined = await gen.refine(
        api_key=_get_api_key(),
        guide=req.guide,
        trade_prices=req.trade_prices,
        budget_chaos=req.budget_chaos,
        history=history,
        message=req.message,
        provider=settings.ai_provider,
    )

    log_usage(user["id"], "refine_build", 0)

    # Resolve passive tree URLs from key_nodes
    refined_dict = refined.model_dump(mode="json")
    try:
        refined_dict = await resolve_guide_tree_urls(refined_dict)
    except Exception:
        pass  # Non-critical

    return refined_dict


@router.post("/resolve-tree-urls")
async def resolve_tree_urls(
    req: ResolveTreeUrlsRequest, user: dict = Depends(require_subscription)
):
    """Resolve passive tree URLs for a BuildGuide's key_nodes."""
    result = await resolve_guide_tree_urls(req.guide, req.tree_version)
    log_usage(user["id"], "resolve_tree_urls", 0)
    return result
