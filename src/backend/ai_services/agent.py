from dataclasses import dataclass
from typing import Sequence
import aiosqlite

from pydantic_ai import Agent, Tool
from pydantic_ai.models.groq import GroqModel
from config.settings import Settings


@dataclass
class Dependencies:
    settings: Settings
    sqlite_db: aiosqlite.Connection   # <-- direct SQLite connection (NOT generator)


def create_groq_agent(
    groq_model: GroqModel,
    tools: Sequence[Tool[Dependencies]],
    system_prompt: str,
) -> Agent[Dependencies]:
    """
    Creates a PydanticAI Agent (compatible with your installed version).
    No unsupported arguments like `returns`, `stream`, or `return_tools_output`.
    """

    return Agent(
        model=groq_model,
        deps_type=Dependencies,
        system_prompt=system_prompt,
        tools=tools,
    )
