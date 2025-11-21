from dataclasses import dataclass
from typing import Sequence
import aiosqlite

from pydantic_ai import Agent, Tool
from pydantic_ai.models.groq import GroqModel
from config.settings import Settings


@dataclass
class Dependencies:
    settings: Settings
    sqlite_db: aiosqlite.Connection   # <-- DIRECT SQLite connection (never generator)


def create_groq_agent(
    groq_model: GroqModel,
    tools: Sequence[Tool[Dependencies]],
    system_prompt: str,
) -> Agent[Dependencies]:
    """
    Creates a PydanticAI Agent that supports:
    - Groq model
    - Streaming
    - All banking tools you register
    - Dependencies injected from FastAPI lifespan

    NOTE:
    - Do NOT use unsupported args like `return_tools_output`, `stream`, `returns`, etc.
    - The tools list must include ALL tools the model may call.
    """

    return Agent(
        model=groq_model,
        deps_type=Dependencies,
        system_prompt=system_prompt,
        tools=tools,                 # <--- MOST IMPORTANT (must include all tools)
        end_strategy="early",        # clean finishing behavior
    )
