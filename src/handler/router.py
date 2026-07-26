import logging
from typing import Sequence
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from voyageai.client_async import AsyncClient

from handler.knowledge_base_answers import KnowledgeBaseAnswers
from models import Message
from whatsapp.jid import parse_jid
from utils.chat_text import chat2text
from utils.opt_out import get_opt_out_map
from whatsapp import WhatsAppClient
from config import Settings
from .base_handler import BaseHandler
from services.prompt_manager import prompt_manager


# Creating an object
logger = logging.getLogger(__name__)


class IntentEnum(str, Enum):
    summarize = "summarize"
    ask_question = "ask_question"
    about = "about"
    other = "other"


class Intent(BaseModel):
    intent: IntentEnum = Field(
        description="""The intent of the message.
- summarize: Summarize TODAY's chat messages, or catch up on the chat messages FROM TODAY ONLY. This will trigger the summarization of the chat messages. This is only relevant for queries about TODDAY chat. A query across a broader timespan is classified as ask_question
- ask_question: Ask a question, OR request an opinion/analysis/explanation, OR any other request (even phrased as a command, e.g. "tell the group...", "give your take on...", "explain...") that requires drawing on the collective knowledge of the group to answer. INCLUDES questions/requests about the group itself (its purpose, topic, rules, members, history, ongoing situations, etc.). This will trigger the knowledge base to answer.
- about: ONLY when the user asks about the BOT itself as an assistant/program (e.g. "who are you", "what can you do", "are you a bot"). NEVER use this for questions or requests about the group. This will trigger the about section.
- other: ONLY for messages that are unrelated to the group's context and don't fit any category above (e.g. small talk, greetings). When in doubt between other and ask_question, prefer ask_question. This will trigger the default response."""
    )


class Router(BaseHandler):
    def __init__(
        self,
        session: AsyncSession,
        whatsapp: WhatsAppClient,
        embedding_client: AsyncClient,
        settings: Settings,
    ):
        self.settings = settings
        self.ask_knowledge_base = KnowledgeBaseAnswers(
            session, whatsapp, embedding_client, settings
        )
        super().__init__(session, whatsapp, embedding_client)

    async def __call__(self, message: Message):
        if not message.text:
            return

        route = await self._route(message.text)
        match route:
            case IntentEnum.summarize:
                await self.summarize(message)
            case IntentEnum.ask_question:
                await self.ask_knowledge_base(message)
            case IntentEnum.about:
                await self.about(message)
            case IntentEnum.other:
                await self.default_response(message)

    async def _route(self, message: str) -> IntentEnum:
        agent = Agent(
            model=self.settings.model_name,
            system_prompt=prompt_manager.render("intent.j2"),
            output_type=Intent,
        )

        result = await agent.run(message)
        return result.output.intent

    async def summarize(self, message: Message):
        time_24_hours_ago = datetime.now() - timedelta(hours=24)
        stmt = (
            select(Message)
            .where(Message.chat_jid == message.chat_jid)
            .where(Message.timestamp >= time_24_hours_ago)
            .order_by(desc(Message.timestamp))
            .limit(30)
        )
        res = await self.session.exec(stmt)
        messages: Sequence[Message] = res.all()

        # Get opt-out map for all senders in the history + current sender
        all_jids = {m.sender_jid for m in messages}
        all_jids.add(message.sender_jid)
        opt_out_map = await get_opt_out_map(self.session, list(all_jids))

        agent = Agent(
            model=self.settings.model_name,
            system_prompt=prompt_manager.render("summarize.j2"),
            output_type=str,
        )

        sender_user = parse_jid(message.sender_jid).user
        sender_display = opt_out_map.get(sender_user, f"@{sender_user}")

        response = await agent.run(
            f"{sender_display}: {message.text}\n\n # History:\n {chat2text(list(messages), opt_out_map)}"
        )
        await self.send_message(
            message.chat_jid,
            response.output,
            # in_reply_to=message.message_id,
        )

    async def about(self, message):
        await self.send_message(
            message.chat_jid,
            "Sou o Mini-me, um bot de IA criado para ajudar a cuidar da mamãe. Posso responder perguntas sobre os cuidados, decisões tomadas no grupo e te atualizar sobre as mensagens do dia.",
            # in_reply_to=message.message_id,
        )

    async def default_response(self, message):
        await self.send_message(
            message.chat_jid,
            "Desculpe, mas acho que não posso ajudar com isso agora 😅.\n Posso ajudar você a se atualizar sobre as mensagens do chat ou responder perguntas com base no conhecimento do grupo.",
            # in_reply_to=message.message_id,
        )
