import logging
from typing import Annotated, Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from voyageai.client_async import AsyncClient

from config import Settings
from handler.knowledge_base_answers import KnowledgeBaseAnswers
from models import Group, Message
from whatsapp import WhatsAppClient
from .deps import get_db_async_session, get_settings, get_text_embebedding, get_whatsapp

router = APIRouter()
logger = logging.getLogger(__name__)


class AskAndReplyRequest(BaseModel):
    group_name: str = Field(description="Name of the managed group whose knowledge base to query")
    chat_jid: str = Field(description="WhatsApp JID to send the answer to (need not be the group itself)")
    question: str = Field(description="Natural-language question")


@router.post("/kb/ask_and_reply")
async def ask_and_reply(
    request: AskAndReplyRequest,
    session: Annotated[AsyncSession, Depends(get_db_async_session)],
    whatsapp: Annotated[WhatsAppClient, Depends(get_whatsapp)],
    embedding_client: Annotated[AsyncClient, Depends(get_text_embebedding)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Dict[str, Any]:
    """
    Answer a question against a managed group's knowledge base and send the
    reply directly over WhatsApp to `chat_jid` - which need not be that group
    (e.g. it can be the asker's own DM). Same cross-group pattern as the
    /kb_qa chat command (handler/kb_qa.py), triggered over HTTP instead.
    """
    stmt = select(Group).where(
        col(Group.group_name).ilike(request.group_name),
        Group.managed == True,  # noqa: E712  https://stackoverflow.com/a/18998106
    )
    groups = list((await session.exec(stmt)).all())

    if not groups:
        stmt = select(Group).where(
            col(Group.group_name).ilike(f"%{request.group_name}%"),
            Group.managed == True,  # noqa: E712
        )
        groups = list((await session.exec(stmt)).all())

    if not groups:
        raise HTTPException(
            status_code=404, detail=f"No managed group found matching '{request.group_name}'"
        )
    if len(groups) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Multiple groups match '{request.group_name}': "
            + ", ".join(g.group_name or g.group_jid for g in groups),
        )
    target_group = groups[0]

    qa_message = Message(
        message_id=f"admin-ask-{uuid4()}",
        text=request.question,
        chat_jid=request.chat_jid,
        sender_jid=request.chat_jid,
        group_jid=target_group.group_jid,
    )
    # group_jid alone isn't enough: message.group is None on a transient/unpersisted
    # object regardless of lazy="selectin" (that's a query-time eager-load strategy,
    # not something populated by manual construction), and KnowledgeBaseAnswers scopes
    # its search on `if message.group:`. Must assign it explicitly.
    qa_message.group = target_group

    await KnowledgeBaseAnswers(session, whatsapp, embedding_client, settings)(qa_message)

    logger.info(
        f"Answered ask_and_reply for group '{target_group.group_name}' -> {request.chat_jid}"
    )

    return {"status": "sent", "group": target_group.group_name, "chat_jid": request.chat_jid}
