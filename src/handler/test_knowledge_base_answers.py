from unittest.mock import AsyncMock, Mock

import pytest
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

from config import Settings
from handler.knowledge_base_answers import KnowledgeBaseAnswers


@pytest.fixture
def mock_whatsapp():
    return AsyncMock()


@pytest.fixture
def mock_embedding_client():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    return Mock(spec=Settings, model_name="test-model")


@pytest.mark.asyncio
async def test_generation_agent_has_web_search_tool(
    mock_session,
    mock_whatsapp,
    mock_embedding_client,
    mock_settings,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_kwargs = {}

    def mock_agent_init(self, *args, **kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(Agent, "__init__", mock_agent_init)
    monkeypatch.setattr(
        Agent, "run", AsyncMock(return_value=AgentRunResult(output="answer"))
    )

    handler = KnowledgeBaseAnswers(
        mock_session, mock_whatsapp, mock_embedding_client, mock_settings
    )
    await handler.generation_agent(
        "query", "topics", "user@s.whatsapp.net", [], {}
    )

    assert "tools" in captured_kwargs
    tool_names = {tool.name for tool in captured_kwargs["tools"]}
    assert "duckduckgo_search" in tool_names
