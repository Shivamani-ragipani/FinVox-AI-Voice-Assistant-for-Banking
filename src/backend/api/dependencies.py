from typing import AsyncIterator, cast
from uuid import uuid4

from fastapi import WebSocket
from groq import AsyncGroq
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from pydantic import UUID4
from pydantic_ai import Agent

from config.settings import get_settings
from nlp_processor.text_to_speech import TextToSpeech
from ai_services.agent import Dependencies


async def get_db_conn(websocket: WebSocket) -> AsyncIterator[AsyncConnection]:
    """
    Get PostgreSQL async connection from pool.
    """
    db_pool = cast(AsyncConnectionPool, websocket.state.pool)

    async with db_pool.connection() as conn:
        yield conn


async def get_conversation_id() -> UUID4:
    """
    Generate unique conversation ID.
    """
    return uuid4()


async def get_agent_dependencies(websocket: WebSocket) -> Dependencies:
    """
    Pass correct dependencies to the Agent.
    - Uses SQLite connection created in lifespan.py
    - Uses Settings
    """
    return Dependencies(
        settings=get_settings(),
        sqlite_db=websocket.app.state.sqlite_db,  # ✅ CORRECT FIX
    )


async def get_groq_client(websocket: WebSocket) -> AsyncGroq:
    """
    Returns the Groq client stored in app state.
    """
    return websocket.state.groq_client


async def get_agent(websocket: WebSocket) -> Agent:
    """
    Returns the Groq Agent instance.
    """
    return websocket.state.groq_agent


async def get_tts_handler(websocket: WebSocket) -> TextToSpeech:
    """
    Returns Text-to-Speech handler (no OpenAI or Groq required).
    """
    return TextToSpeech()
