from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.seed_knowledge_api import SeedKnowledgeRequest, SeedTopic, seed_knowledge
from models import Group


@pytest.fixture
def mock_embedding_client():
    client = AsyncMock()
    client.embed = AsyncMock(
        side_effect=lambda input, **kwargs: Mock(
            embeddings=[[0.1] * 1024 for _ in input], total_tokens=10
        )
    )
    return client


def _mock_group_lookup(mock_session, groups):
    mock_result = Mock()
    mock_result.all.return_value = groups
    mock_session.exec.side_effect = None
    mock_session.exec.return_value = mock_result


@pytest.mark.asyncio
async def test_seed_knowledge_success(mock_session, mock_embedding_client):
    group = Group(group_jid="target@g.us", group_name="target_group", managed=True)
    _mock_group_lookup(mock_session, [group])

    request = SeedKnowledgeRequest(
        group_name="target_group",
        topics=[SeedTopic(subject="Purpose", content="This group is about testing.")],
    )

    response = await seed_knowledge(request, mock_session, mock_embedding_client)

    assert response["status"] == "success"
    assert response["group"] == "target_group"
    assert response["topics_seeded"] == ["Purpose"]
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_seed_knowledge_no_group_found(mock_session, mock_embedding_client):
    _mock_group_lookup(mock_session, [])

    request = SeedKnowledgeRequest(
        group_name="missing_group",
        topics=[SeedTopic(subject="Purpose", content="content")],
    )

    with pytest.raises(HTTPException) as exc_info:
        await seed_knowledge(request, mock_session, mock_embedding_client)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_seed_knowledge_ambiguous_group(mock_session, mock_embedding_client):
    groups = [
        Group(group_jid="a@g.us", group_name="dup", managed=True),
        Group(group_jid="b@g.us", group_name="dup", managed=True),
    ]
    _mock_group_lookup(mock_session, groups)

    request = SeedKnowledgeRequest(
        group_name="dup",
        topics=[SeedTopic(subject="Purpose", content="content")],
    )

    with pytest.raises(HTTPException) as exc_info:
        await seed_knowledge(request, mock_session, mock_embedding_client)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_seed_knowledge_requires_topics(mock_session, mock_embedding_client):
    request = SeedKnowledgeRequest(group_name="target_group", topics=[])

    with pytest.raises(HTTPException) as exc_info:
        await seed_knowledge(request, mock_session, mock_embedding_client)

    assert exc_info.value.status_code == 400
