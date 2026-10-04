import os
import time
import asyncio
import numpy as np

from faster_whisper import WhisperModel

from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType


TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()

        self.interface_type = InterfaceType.LOCAL

        self.model_size = config.get("model_size", "small")
        self.device = config.get("device", "cpu")
        self.compute_type = config.get("compute_type", "int8")
        self.language = config.get("language", "vi")

        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

        os.makedirs(self.output_dir, exist_ok=True)

        logger.bind(tag=TAG).info(
            f"Loading Faster-Whisper model={self.model_size}, device={self.device}"
        )

        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

        logger.bind(tag=TAG).info("Faster-Whisper loaded")

    def _transcribe(self, pcm_bytes):
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
        )

        text = "".join(segment.text for segment in segments).strip()

        return text

    async def speech_to_text(
        self,
        opus_data,
        session_id,
        artifacts=None,
    ):
        try:
            if artifacts is None:
                return "", None

            start = time.time()

            text = await asyncio.to_thread(
                self._transcribe,
                artifacts.pcm_bytes,
            )

            logger.bind(tag=TAG).info(f"Whisper {time.time() - start:.2f}s: {text}")

            return text, artifacts.file_path

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Faster-Whisper error: {e}",
                exc_info=True,
            )

            return "", None
