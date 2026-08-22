"""Persistent conversation-memory construction."""

from langchain_classic.memory import ConversationSummaryMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory

from src.models.llm_client import llm
from src.utils.config import settings


def create_memory(
    video_id: str,
    user_id: str,
    conversation_id: str,
) -> ConversationSummaryMemory:
    return ConversationSummaryMemory(
        llm=llm,
        chat_memory=SQLChatMessageHistory(
            session_id=f"{user_id}:{conversation_id}:{video_id}",
            connection_string=settings.database_url,
        ),
    )
