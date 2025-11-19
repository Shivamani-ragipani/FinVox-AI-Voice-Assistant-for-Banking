import io
from typing import AsyncIterator
from gtts import gTTS

class TextToSpeech:
    def __init__(
        self,
        voice: str = "en",
        response_format: str = "mp3",
        speed: float = 1.0,
        buffer_size: int = 128,
        sentence_endings: tuple[str, ...] = ("?", "!", ";", ":", "\n"),
        chunk_size: int = 1024 * 5,
    ) -> None:
        self.voice = voice
        self.response_format = response_format
        self.speed = speed
        self.buffer_size = buffer_size
        self.sentence_endings = sentence_endings
        self.chunk_size = chunk_size
        self._buffer = ""

    async def __aenter__(self) -> "TextToSpeech":
        return self

    async def feed(self, text: str) -> AsyncIterator[bytes]:
        self._buffer += text
        if len(self._buffer) >= self.buffer_size or any(
            self._buffer.endswith(se) for se in self.sentence_endings
        ):
            async for chunk in self.flush():
                yield chunk

    async def flush(self) -> AsyncIterator[bytes]:
        if self._buffer:
            async for chunk in self._send_audio(self._buffer):
                yield chunk
            self._buffer = ""

    async def _send_audio(self, text: str) -> AsyncIterator[bytes]:
        tts = gTTS(text=text, lang=self.voice, slow=False)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)

        while True:
            chunk = buffer.read(self.chunk_size)
            if not chunk:
                break
            yield chunk

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        pass
