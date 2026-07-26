from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from api.ask_and_reply_api import AskAndReplyRequest, ask_and_reply
from models import Group


def _mock_group_lookup(mock_session, groups):
    mock_result = Mock()
    mock_result.all.return_value = groups
    mock_session.exec.side_effect = None
    mock_session.exec.return_value = mock_result


@pytest.mark.asyncio
async def test_ask_and_reply_success_scopes_message_to_group(mock_session):
    group = Group(group_jid="target@g.us", group_name="Cuidados Mamis", managed=True)
    _mock_group_lookup(mock_session, [group])

    whatsapp = AsyncMock()
    embedding_client = AsyncMock()
    settings = Mock()

    with patch("api.ask_and_reply_api.KnowledgeBaseAnswers") as MockKB:
        mock_kb_instance = AsyncMock()
        MockKB.return_value = mock_kb_instance

        request = AskAndReplyRequest(
            group_name="Cuidados Mamis",
            chat_jid="19403632605@s.whatsapp.net",
            question="Qual o propósito do grupo?",
        )
        response = await ask_and_reply(request, mock_session, whatsapp, embedding_client, settings)

        assert response == {
            "status": "sent",
            "group": "Cuidados Mamis",
            "chat_jid": "19403632605@s.whatsapp.net",
        }

        mock_kb_instance.assert_called_once()
        sent_message = mock_kb_instance.call_args[0][0]
        assert sent_message.chat_jid == "19403632605@s.whatsapp.net"
        assert sent_message.group_jid == "target@g.us"
        # The critical regression check: .group must be explicitly set, otherwise
        # KnowledgeBaseAnswers.__call__'s `if message.group:` check silently searches
        # unscoped across every group's KB instead of just this one.
        assert sent_message.group is group


@pytest.mark.asyncio
async def test_ask_and_reply_no_group_found(mock_session):
    _mock_group_lookup(mock_session, [])

    request = AskAndReplyRequest(
        group_name="Missing Group", chat_jid="19403632605@s.whatsapp.net", question="q"
    )

    with pytest.raises(HTTPException) as exc_info:
        await ask_and_reply(request, mock_session, AsyncMock(), AsyncMock(), Mock())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_ask_and_reply_ambiguous_group(mock_session):
    groups = [
        Group(group_jid="a@g.us", group_name="dup", managed=True),
        Group(group_jid="b@g.us", group_name="dup", managed=True),
    ]
    _mock_group_lookup(mock_session, groups)

    request = AskAndReplyRequest(
        group_name="dup", chat_jid="19403632605@s.whatsapp.net", question="q"
    )

    with pytest.raises(HTTPException) as exc_info:
        await ask_and_reply(request, mock_session, AsyncMock(), AsyncMock(), Mock())

    assert exc_info.value.status_code == 400
