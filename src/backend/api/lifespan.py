from contextlib import asynccontextmanager
from typing import AsyncIterator, TypedDict
import os
import aiosqlite

from fastapi import FastAPI
from groq import AsyncGroq
from loguru import logger
from openai import AsyncOpenAI
from psycopg_pool import AsyncConnectionPool
from pydantic_ai import Agent, Tool

from config.settings import get_settings
from convo_history_db.actions import create_main_table
from convo_history_db.connection import create_db_connection_pool
from ai_services.agent import Dependencies, create_groq_agent
from ai_services.factories import (
    create_groq_client,
    create_groq_model,
    create_openai_client,
)
from ai_services.tools import (
    get_recent_transactions,
    summarize_spending,
    detect_unusual_spending,
)


class State(TypedDict):
    pool: AsyncConnectionPool
    groq_client: AsyncGroq
    openai_client: AsyncOpenAI
    groq_agent: Agent[Dependencies]
    sqlite_db: aiosqlite.Connection


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[State]:
    settings = get_settings()

    # ---------------------------------------------------------
    # System prompt
    # ---------------------------------------------------------
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    SYSTEM_PROMPT_PATH = os.path.join(
        BASE_DIR, "project_info", "agent_system_prompt.md"
    )

    if not os.path.exists(SYSTEM_PROMPT_PATH):
        raise FileNotFoundError(
            f"System prompt file missing: {SYSTEM_PROMPT_PATH}"
        )

    system_prompt = open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8").read()

    # ---------------------------------------------------------
    # PostgreSQL pool
    # ---------------------------------------------------------
    pool = create_db_connection_pool(settings=settings)

    # ---------------------------------------------------------
    # AI clients
    # ---------------------------------------------------------
    openai_client = create_openai_client(settings=settings)
    groq_client = create_groq_client(settings=settings)
    groq_model = create_groq_model(groq_client=groq_client)

    # ---------------------------------------------------------
    # SQLITE for Transactions
    # ---------------------------------------------------------
    SQLITE_PATH = os.path.join(BASE_DIR, "customer_transaction_db", "transactions.db")

    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)

    if not os.path.exists(SQLITE_PATH):
        raise FileNotFoundError(f"SQLite DB NOT FOUND at: {SQLITE_PATH}")

    sqlite_db = await aiosqlite.connect(SQLITE_PATH)
    sqlite_db.row_factory = aiosqlite.Row

    # ---------------------------------------------------------
    # Tools
    # ---------------------------------------------------------
    tools = [
        Tool(function=get_recent_transactions, takes_ctx=True),
        Tool(function=summarize_spending, takes_ctx=True),
        Tool(function=detect_unusual_spending, takes_ctx=True),
    ]

    groq_agent = create_groq_agent(
        groq_model=groq_model,
        tools=tools,
        system_prompt=system_prompt,
    )

    # ---------------------------------------------------------
    # Startup work
    # ---------------------------------------------------------
    logger.info("Opening database connection pool")
    await pool.open()
    await create_main_table(pool)

    # Save to state (used in dependencies.py)
    app.state.sqlite_db = sqlite_db
    app.state.groq_agent = groq_agent
    app.state.groq_client = groq_client
    app.state.openai_client = openai_client

    yield {
        "pool": pool,
        "groq_client": groq_client,
        "openai_client": openai_client,
        "groq_agent": groq_agent,
        "sqlite_db": sqlite_db,
    }

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------
    logger.info("Closing SQLite DB")
    await sqlite_db.close()

    logger.info("Closing PostgreSQL pool")
    await pool.close()

    logger.info("Closing OpenAI client")
    await openai_client.close()

    logger.info("Closing Groq client")
    await groq_client.close()
