import hashlib
import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from voyageai.client_async import AsyncClient

from models import Group, KBTopic
from models.upsert import bulk_upsert
from utils.voyage_embed_text import voyage_embed_text
from .deps import get_db_async_session, get_text_embebedding

router = APIRouter()
logger = logging.getLogger(__name__)


class SeedTopic(BaseModel):
    subject: str = Field(description="Short title for this piece of background knowledge")
    content: str = Field(description="The background knowledge text itself")


class SeedKnowledgeRequest(BaseModel):
    group_name: str = Field(description="Exact name of the managed group to seed")
    topics: List[SeedTopic]


@router.post("/kb/seed")
async def seed_knowledge(
    request: SeedKnowledgeRequest,
    session: Annotated[AsyncSession, Depends(get_db_async_session)],
    embedding_client: Annotated[AsyncClient, Depends(get_text_embebedding)],
) -> Dict[str, Any]:
    """
    Seed a group's knowledge base with background info that didn't come from
    chat messages (e.g. the group's purpose, rules, glossary). These entries
    are searched the same way as topics extracted from conversations.

    Re-seeding the same `subject` for the same group overwrites that entry.
    """
    if not request.topics:
        raise HTTPException(status_code=400, detail="At least one topic is required")

    stmt = select(Group).where(col(Group.group_name).ilike(request.group_name))
    result = await session.exec(stmt)
    groups = list(result.all())

    if len(groups) == 0:
        raise HTTPException(
            status_code=404, detail=f"No group found matching '{request.group_name}'"
        )
    if len(groups) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Multiple groups match '{request.group_name}': "
            + ", ".join(g.group_name or g.group_jid for g in groups),
        )
    group = groups[0]

    documents = [f"# {t.subject}\n{t.content}" for t in request.topics]
    embeddings = await voyage_embed_text(embedding_client, documents)

    now = datetime.now(timezone.utc)
    kb_topics = [
        KBTopic(
            id=hashlib.sha256(
                f"{group.group_jid}_seed_{t.subject}".encode()
            ).hexdigest(),
            group_jid=group.group_jid,
            start_time=now,
            speakers="",
            subject=t.subject,
            summary=t.content,
            embedding=emb,
        )
        for t, emb in zip(request.topics, embeddings)
    ]
    await bulk_upsert(session, kb_topics)
    await session.commit()

    logger.info(
        f"Seeded {len(kb_topics)} KB topic(s) for group '{group.group_name}'"
    )

    return {
        "status": "success",
        "group": group.group_name,
        "topics_seeded": [t.subject for t in request.topics],
    }
