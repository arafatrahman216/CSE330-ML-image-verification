import json
import math
import mimetypes
import os
import tempfile
import time
import urllib.request
from uuid import uuid4
from collections.abc import Sequence
from urllib.parse import urlparse

from gradio_client import Client, handle_file

from app.config import Settings


class VoiceEmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token = settings.voice_embedding_api_key or None
        self._client: Client | None = None
        self._http_embedding_url = self._resolve_http_embedding_url(settings.voice_embedding_api_url)

    def _build_client(self, source: str) -> Client:
        candidates = [source]

        parsed = urlparse(source)
        if parsed.scheme and parsed.netloc and "huggingface.co" in parsed.netloc:
            path = parsed.path.strip("/")
            if path.startswith("spaces/"):
                space_id = path[len("spaces/") :]
                if space_id:
                    candidates.append(space_id)

        last_exc: Exception | None = None
        for candidate in candidates:
            try:
                return Client(candidate, hf_token=self._token)
            except Exception as exc:
                last_exc = exc

        raise RuntimeError(
            "Unable to initialize voice embedding client. Set VOICE_EMBEDDING_API_URL "
            "to a valid Gradio source (for example: enayetalvee/speaker-embedding-resnet34)."
        ) from last_exc

    @staticmethod
    def _resolve_http_embedding_url(source: str) -> str | None:
        parsed = urlparse(source)

        if parsed.scheme and parsed.netloc:
            if "huggingface.co" in parsed.netloc:
                path = parsed.path.strip("/")
                if path.startswith("spaces/"):
                    rest = path[len("spaces/") :]
                    parts = rest.split("/", 1)
                    if len(parts) == 2 and all(parts):
                        return f"https://{parts[0]}-{parts[1]}.hf.space/embedding"
                return None

            if parsed.netloc.endswith(".hf.space"):
                base = source.rstrip("/")
                return f"{base}/embedding"

            return None

        if "/" in source:
            parts = source.split("/", 1)
            if len(parts) == 2 and all(parts):
                return f"https://{parts[0]}-{parts[1]}.hf.space/embedding"

        return None

    def get_embedding(self, audio_bytes: bytes, file_extension: str) -> list[float]:
        result = self._predict(audio_bytes, file_extension)
        embedding = self._extract_embedding(result)

        expected_dim = self._settings.voice_qdrant_vector_size
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Voice embedding dimension {len(embedding)} does not match expected {expected_dim}"
            )

        return embedding

    def _predict(self, audio_bytes: bytes, file_extension: str):
        retries = max(1, int(self._settings.voice_embedding_api_max_retries))
        base_delay = max(0.0, float(self._settings.voice_embedding_api_retry_delay_seconds))

        if self._http_embedding_url:
            result = None
            last_error: Exception | None = None
            for attempt in range(1, retries + 1):
                try:
                    result = self._predict_http(audio_bytes, file_extension)
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt >= retries:
                        break
                    time.sleep(base_delay * attempt)

            if result is not None:
                return result

            # Fall through to gradio client path as a fallback if HTTP API fails.

        suffix = f".{file_extension}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        result = None
        last_error: Exception | None = None

        try:
            for attempt in range(1, retries + 1):
                try:
                    if self._client is None:
                        self._client = self._build_client(self._settings.voice_embedding_api_url)

                    result = self._client.predict(
                        **{
                            self._settings.voice_embedding_api_input_name: handle_file(temp_path),
                            "api_name": self._settings.voice_embedding_api_name,
                        }
                    )
                    break
                except TypeError:
                    result = self._client.predict(
                        handle_file(temp_path),
                        api_name=self._settings.voice_embedding_api_name,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt >= retries:
                        break
                    time.sleep(base_delay * attempt)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if result is None:
            if self._is_timeout_error(last_error):
                raise TimeoutError(
                    f"Voice embedding API timed out after {retries} attempt(s)"
                ) from last_error
            raise RuntimeError(f"Voice embedding API request failed: {last_error}") from last_error

        return result

    def _predict_http(self, audio_bytes: bytes, file_extension: str):
        if not self._http_embedding_url:
            raise RuntimeError("HTTP embedding endpoint is not configured")

        boundary = f"----Boundary{uuid4().hex}"
        mime = mimetypes.guess_type(f"x.{file_extension}")[0] or "application/octet-stream"
        filename = f"audio.{file_extension}"

        body = b"\r\n".join(
            [
                f"--{boundary}".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"'
                ).encode("utf-8"),
                f"Content-Type: {mime}".encode("utf-8"),
                b"",
                audio_bytes,
                f"--{boundary}--".encode("utf-8"),
                b"",
            ]
        )

        req = urllib.request.Request(
            self._http_embedding_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=45) as response:
            payload = response.read().decode("utf-8")

        return json.loads(payload)

    def _extract_embedding(self, raw: object) -> list[float]:
        candidate = raw

        if isinstance(raw, str):
            try:
                candidate = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("Voice embedding payload string is not valid JSON") from exc

        if isinstance(candidate, dict):
            for key in ("embedding", "vector", "data", "value"):
                if key in candidate:
                    candidate = candidate[key]
                    break

        # Some spaces return [embedding, ...] or [[...]]
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
            if len(candidate) == 0:
                raise ValueError("Voice embedding vector is empty")
            first = candidate[0]
            if isinstance(first, Sequence) and not isinstance(first, (str, bytes, bytearray)):
                candidate = first

        if not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes, bytearray)):
            raise ValueError("Voice embedding payload is not a numeric sequence")

        parsed: list[float] = []
        for value in candidate:
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Voice embedding contains non-numeric values") from exc
            if not math.isfinite(number):
                raise ValueError("Voice embedding contains non-finite values")
            parsed.append(number)

        if not parsed:
            raise ValueError("Voice embedding vector is empty")

        return parsed

    @staticmethod
    def _is_timeout_error(exc: Exception | None) -> bool:
        if exc is None:
            return False
        text = str(exc).lower()
        timeout_tokens = (
            "timed out",
            "timeout",
            "read operation timed out",
            "readtimeout",
        )
        return isinstance(exc, TimeoutError) or any(token in text for token in timeout_tokens)
