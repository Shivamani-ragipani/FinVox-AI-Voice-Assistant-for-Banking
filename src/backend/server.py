from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import logfire
from fastapi import Depends, FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect
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
    title="Finvox AI Banking Assistant",
    lifespan=lifespan,
)

logfire.configure()
logfire.instrument_fastapi(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
        while True:
            incoming_audio_bytes = await websocket.receive_bytes()

            logger.info(f"Received audio bytes: {len(incoming_audio_bytes)} bytes")
            logger.info("Starting transcription process")

            transcription = await transcribe_audio_data(
                audio_data=incoming_audio_bytes,
                api_client=groq_client,
                model_name="whisper-large-v3-turbo",
            )

            logger.info(f"STT Transcription: '{transcription}'")

            if not transcription or not transcription.strip():
                continue

            await websocket.send_text(f"Client: {transcription}")

            # Store user message
            await store_message(
                conn=db_conn,
                conversation_id=conversation_id,
                sender="user",
                content=transcription,
            )

            conversation_history = await get_conversation_history(
                conn=db_conn,
                conversation_id=conversation_id,
            )

            # Count ONLY user messages
            try:
                user_msg_count = len([
                    m for m in conversation_history
                    if m.get("sender") == "user"
                ])
            except Exception:
                user_msg_count = len(conversation_history)

            logger.info(f"User message count: {user_msg_count}")

            agent_messages = format_messages_for_agent(conversation_history)

            normalized = transcription.strip().lower()

            # Greeting detection
            is_greeting = normalized in {
                "hi", "hello", "hey", "hai",
                "hi.", "hello.", "hey.", "hai.",
            }

            is_first_user_turn = user_msg_count <= 1

            # ------ FIXED: Removed startswith("thank") ------
            if is_first_user_turn and is_greeting:
                greeting = (
                    "Hello Shivamani! I can help you with your banking information. "
                    "You can ask me to check your balance, show your recent transactions, "
                    "or tell you the latest schemes from SBI or HDFC."
                )

                async with tts_handler:
                    async for audio_chunk in tts_handler.feed(text=greeting):
                        await websocket.send_bytes(audio_chunk)
                    async for audio_chunk in tts_handler.flush():
                        await websocket.send_bytes(audio_chunk)

                await websocket.send_text(f"Agent: {greeting}")

                await store_message(
                    conn=db_conn,
                    conversation_id=conversation_id,
                    sender="agent",
                    content=greeting,
                )

                continue
            # ------ END FIX ------

            logger.info("Starting agent generation process")

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

            # Store agent response
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
