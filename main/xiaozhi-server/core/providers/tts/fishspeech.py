import base64
import requests
import ormsgpack
from pathlib import Path
from pydantic import BaseModel, Field, conint, model_validator
from typing_extensions import Annotated
from typing import Literal
from core.utils.util import check_model_key, parse_string_to_list
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str

    @model_validator(mode="before")
    def decode_audio(cls, values):
        audio = values.get("audio")
        if (
            isinstance(audio, str) and len(audio) > 255
        ):  # Kiểm tra xem âm thanh có phải là chuỗi không (Base64)
            try:
                values["audio"] = base64.b64decode(audio)
            except Exception as e:
                # Nếu âm thanh không phải là chuỗi base64 hợp lệ, chúng tôi sẽ bỏ qua nó và để máy chủ xử lý.
                pass
        return values

    def __repr__(self) -> str:
        return f"ServeReferenceAudio(text={self.text!r}, audio_size={len(self.audio)})"


class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: Annotated[int, conint(ge=100, le=300, strict=True)] = 200
    # Định dạng âm thanh
    format: Literal["wav", "pcm", "mp3"] = "wav"
    # Âm thanh tham khảo cho việc học theo ngữ cảnh
    references: list[ServeReferenceAudio] = []
    # Reference id
    # Ví dụ: nếu bạn muốn sử dụng https://fish.audio/m/7f92f8afb8ec43bf81429cc1c9199cb1/
    # Just pass 7f92f8afb8ec43bf81429cc1c9199cb1
    reference_id: str | None = None
    seed: int | None = None
    use_memory_cache: Literal["on", "off"] = "off"
    # Chuẩn hóa văn bản cho en & zh, điều này tăng tính ổn định cho số
    normalize: bool = True
    # không thường được sử dụng dưới đây
    streaming: bool = False
    max_new_tokens: int = 1024
    top_p: Annotated[float, Field(ge=0.1, le=1.0, strict=True)] = 0.7
    repetition_penalty: Annotated[float, Field(ge=0.9, le=2.0, strict=True)] = 1.2
    temperature: Annotated[float, Field(ge=0.1, le=1.0, strict=True)] = 0.7

    class Config:
        # Cho phép các loại tùy ý cho các loại liên quan đến pytorch
        arbitrary_types_allowed = True


def audio_to_bytes(file_path):
    if not file_path or not Path(file_path).exists():
        return None
    with open(file_path, "rb") as wav_file:
        wav = wav_file.read()
    return wav


def read_ref_text(ref_text):
    path = Path(ref_text)
    if path.exists() and path.is_file():
        with path.open("r", encoding="utf-8") as file:
            return file.read()
    return ref_text


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.reference_id = (
            None if not config.get("reference_id") else config.get("reference_id")
        )
        self.reference_audio = parse_string_to_list(
            config.get("ref_audio")
            if config.get("ref_audio")
            else config.get("reference_audio")
        )
        self.reference_text = parse_string_to_list(
            config.get("ref_text")
            if config.get("ref_text")
            else config.get("reference_text")
        )
        self.audio_file_type = config.get("response_format", "wav")
        self.api_key = config.get("api_key", "YOUR_API_KEY")
        model_key_msg = check_model_key("FishSpeech TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            return
        self.normalize = str(config.get("normalize", True)).lower() in (
            "true",
            "1",
            "yes",
        )

        # Xử lý trường hợp chuỗi trống
        channels = config.get("channels", "1")
        rate = config.get("rate", "44100")
        max_new_tokens = config.get("max_new_tokens", "1024")
        chunk_length = config.get("chunk_length", "200")

        self.channels = int(channels) if channels else 1
        self.rate = int(rate) if rate else 44100
        self.max_new_tokens = int(max_new_tokens) if max_new_tokens else 1024
        self.chunk_length = int(chunk_length) if chunk_length else 200

        # Xử lý trường hợp chuỗi trống
        top_p = config.get("top_p", "0.7")
        temperature = config.get("temperature", "0.7")
        repetition_penalty = config.get("repetition_penalty", "1.2")

        self.top_p = float(top_p) if top_p else 0.7
        self.temperature = float(temperature) if temperature else 0.7
        self.repetition_penalty = (
            float(repetition_penalty) if repetition_penalty else 1.2
        )

        self.streaming = str(config.get("streaming", False)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.use_memory_cache = config.get("use_memory_cache", "on")
        self.seed = int(config.get("seed")) if config.get("seed") else None
        self.api_url = config.get("api_url", "http://127.0.0.1:8080/v1/tts")

    async def text_to_speak(self, text, output_file):
        # Chuẩn bị dữ liệu tham khảo
        byte_audios = [audio_to_bytes(ref_audio) for ref_audio in self.reference_audio]
        ref_texts = [read_ref_text(ref_text) for ref_text in self.reference_text]

        data = {
            "text": text,
            "references": [
                ServeReferenceAudio(audio=audio if audio else b"", text=ref_text)
                for ref_text, audio in zip(ref_texts, byte_audios)
            ],
            "reference_id": self.reference_id,
            "normalize": self.normalize,
            "format": self.audio_file_type,
            "max_new_tokens": self.max_new_tokens,
            "chunk_length": self.chunk_length,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "use_memory_cache": self.use_memory_cache,
            "seed": self.seed,
        }

        pydantic_data = ServeTTSRequest(**data)

        response = requests.post(
            self.api_url,
            data=ormsgpack.packb(
                pydantic_data, option=ormsgpack.OPT_SERIALIZE_PYDANTIC
            ),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/msgpack",
            },
            timeout=self.tts_timeout,
        )

        if response.status_code == 200:
            audio_content = response.content

            if output_file:
                with open(output_file, "wb") as audio_file:
                    audio_file.write(audio_content)
            else:
                return audio_content

        else:
            error_msg = f"Request failed with status code {response.status_code}"
            print(error_msg)
            print(response.json())
            raise Exception(error_msg)
