
import asyncio
import logging

from faster_whisper import WhisperModel
from livekit.agents import stt
from livekit import rtc
import numpy as np
logger = logging.getLogger("local-stt")


class LocalWhisperSTT(stt.STT):
    def __init__(self, model_size="base"):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )

        self.whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )

    async def _recognize_impl(
        self,
        buffer: rtc.AudioFrame,
        *,
        language=None,
        conn_options=None,
    ) -> stt.SpeechEvent:
        audio_data = buffer.data

        audio = np.frombuffer(audio_data,dtype=np.int16).astype(np.float32) / 32768.0

        segments, info = await asyncio.to_thread(
            self.whisper_model.transcribe,
            audio,
            language=language or "en",
        )

        text = " ".join(segment.text for segment in segments).strip()

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    text=text,
                    language=info.language,
                )
            ],
        )
