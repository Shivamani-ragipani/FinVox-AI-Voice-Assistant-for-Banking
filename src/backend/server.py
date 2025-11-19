from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import logfire
from fastapi import Depends, FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect 
from fastapi.responses import HTMLResponse
from groq import AsyncGroq
from loguru import logger
from psycopg import AsyncConnection
from pydantic import UUID4
from pydantic_ai import Agent

from api.dependencies import (
    get_agent,
    get_agent_dependencies,
    get_conversation_id,
    get_db_conn,
    get_groq_client,
    get_tts_handler,
)
from api.lifespan import app_lifespan as lifespan

from convo_history_db.actions import get_conversation_history, store_message
from nlp_processor.speech_to_text import transcribe_audio_data
from nlp_processor.text_to_speech import TextToSpeech

from ai_services.agent import Dependencies
from ai_services.utils import format_messages_for_agent

app = FastAPI(
    title="Voice to Voice Banking Assistant",
    lifespan=lifespan
)

# logfire setup
logfire.configure()
logfire.instrument_fastapi(app)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------
@app.get("/health")
async def health(websocket: WebSocket) -> dict[str, str]:
    """Simple DB health check."""
    try:
        async for db_conn in get_db_conn(websocket):
            return {"status": "ok"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------
# WEBSOCKET: VOICE-TO-VOICE BANK ASSISTANT
# ---------------------------------------------------------
@app.websocket("/voice_stream")
async def voice_to_voice(
    websocket: WebSocket,
    conversation_id: UUID4 = Depends(get_conversation_id),
    db_conn: AsyncConnection = Depends(get_db_conn),
    groq_client: AsyncGroq = Depends(get_groq_client),
    agent: Agent[Dependencies] = Depends(get_agent),
    agent_deps: Dependencies = Depends(get_agent_dependencies),
    tts_handler: TextToSpeech = Depends(get_tts_handler),
):
    await websocket.accept()
    logger.info(f"New websocket connection for conversation {conversation_id}")

    try:
        while True:   # ← KEEP SOCKET ALIVE FOREVER
            incoming_audio_bytes = await websocket.receive_bytes()

            # ------------------------------
            # 1. TRANSCRIBE
            # ------------------------------
            logger.info("Starting transcription process")

            transcription = await transcribe_audio_data(
                audio_data=incoming_audio_bytes,
                api_client=groq_client,
                model_name="whisper-large-v3-turbo",
            )

            await websocket.send_text(f"Client: {transcription}")

            await store_message(
                conn=db_conn,
                conversation_id=conversation_id,
                sender="user",
                content=transcription,
            )

            # ------------------------------
            # 2. GET HISTORY + FORMAT
            # ------------------------------
            conversation_history = await get_conversation_history(
                conn=db_conn,
                conversation_id=conversation_id,
            )

            agent_messages = format_messages_for_agent(conversation_history)

            # ------------------------------
            # 3. RUN AGENT + STREAM AUDIO
            # ------------------------------
            logger.info("Starting generation process")
            full_response_text = ""

            async with tts_handler:
                async with agent.run_stream(
                    user_prompt=transcription,
                    message_history=agent_messages,
                    deps=agent_deps,
                ) as result:

                    async for message in result.stream_text(delta=True):
                        full_response_text += message

                        async for audio_chunk in tts_handler.feed(text=message):
                            await websocket.send_bytes(audio_chunk)

                async for audio_chunk in tts_handler.flush():
                    await websocket.send_bytes(audio_chunk)

            await websocket.send_text(f"Agent: {full_response_text}")

            await store_message(
                conn=db_conn,
                conversation_id=conversation_id,
                sender="agent",
                content=full_response_text,
            )

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception(f"Error in websocket: {e}")
