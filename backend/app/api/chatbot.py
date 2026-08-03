from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette import EventSourceResponse

from ..core.dependencies import get_agent_service, get_chat_store, require_marcopolo_access
from ..models.api import ChatCreateRequest, ChatCreateResponse
from ..services.auth import UserSession
from ..services.chatbot import ChatStore, IntegrationDemoAgentService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatCreateResponse)
async def create_chat_run(
    request: ChatCreateRequest,
    user_session: UserSession = Depends(require_marcopolo_access),
    chat_store: ChatStore = Depends(get_chat_store),
) -> ChatCreateResponse:
    chat_run = chat_store.create(request.message, user_session)
    return ChatCreateResponse(chat_id=chat_run.chat_id)


@router.get("/{chat_id}/stream")
async def stream_chat_run(
    chat_id: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    chat_store: ChatStore = Depends(get_chat_store),
    agent_service: IntegrationDemoAgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    chat_run = chat_store.get(chat_id)
    if chat_run is None:
        raise HTTPException(status_code=404, detail="Chat run not found.")
    if not chat_run.user_session.user or chat_run.user_session.user.subject != user_session.user.subject:
        raise HTTPException(status_code=403, detail="Chat run belongs to a different user.")

    return EventSourceResponse(agent_service.stream_chat(chat_run))
