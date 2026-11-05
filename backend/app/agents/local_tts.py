
import asyncio
import logging
import uuid
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

from livekit.agents import tts
from livekit.agents.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
)

logger = logging.getLogger("local-kokoro-tts")


class LocalKokoroTTS(tts.TTS):

    def __init__(
        self,
        model_path="models/kokoro/kokoro-v1.0.onnx",
        voices_path="models/kokoro/voices-v1.0.bin",
        voice="af_heart",
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
            ),
            sample_rate=24000,
            num_channels=1,
        )

        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        self.voice = voice

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Kokoro model not found: {self.model_path.resolve()}"
            )

        if not self.voices_path.exists():
            raise FileNotFoundError(
                f"Kokoro voices not found: {self.voices_path.resolve()}"
            )

        logger.info("Loading Kokoro ONNX model...")

        self.kokoro_model = Kokoro(
            model_path=str(self.model_path),
            voices_path=str(self.voices_path),
        )

        logger.info("Kokoro TTS initialized successfully.")

    @property
    def model(self):
        return "kokoro-v1.0"

    @property
    def provider(self):
        return "local-kokoro"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "KokoroStream":

        return KokoroStream(
            owner=self,
            text=text,
            conn_options=conn_options,
        )


class KokoroStream(tts.ChunkedStream):

    def __init__(
        self,
        *,
        owner: LocalKokoroTTS,
        text: str,
        conn_options: APIConnectOptions,
    ):

        super().__init__(
            tts=owner,
            input_text=text,
            conn_options=conn_options,
        )

        self.kokoro_model = owner.kokoro_model
        self.voice = owner.voice

    async def _run(self, output_emitter: tts.AudioEmitter):

        logger.info("Generating audio with Kokoro...")

        try:

            audio, sample_rate = await asyncio.to_thread(
                self.kokoro_model.create,
                self._input_text,
                voice=self.voice,
                speed=1.0,
                lang="en-us",
            )

            audio = np.asarray(audio, dtype=np.float32)

            if audio.size == 0:
                raise RuntimeError("Kokoro returned empty audio.")

            audio = np.clip(audio, -1.0, 1.0)

            pcm_audio = (audio * 32767).astype(np.int16)

            output_emitter.initialize(
                request_id=str(uuid.uuid4()),
                sample_rate=sample_rate,
                num_channels=1,
                mime_type="audio/pcm",
            )

            output_emitter.push(pcm_audio.tobytes())
            output_emitter.flush()

            logger.info("Kokoro audio generation completed.")

        except Exception:
            logger.exception("Kokoro TTS generation failed.")
            raise
