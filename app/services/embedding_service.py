import json
import math
import mimetypes
import os
import tempfile
import time
import urllib.request
from collections.abc import Sequence

from gradio_client import Client, handle_file

from app.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        token = settings.embedding_api_key or None
        self._client = Client(settings.embedding_api_url, hf_token=token)

    def get_embedding(self, image_bytes: bytes, file_extension: str) -> list[float]:
        result = self._predict(image_bytes, file_extension)

        if not isinstance(result, (list, tuple)) or len(result) < 3:
            raise RuntimeError("Embedding API returned an unexpected response format")

        embedding = self._extract_embedding(result[0])
        reported_dim = self._extract_dimension(result[2])

        if len(embedding) != reported_dim:
            raise ValueError(
                f"Embedding length mismatch: len={len(embedding)} but reported_dim={reported_dim}"
            )

        expected_dim = self._settings.qdrant_vector_size
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding dimension {len(embedding)} does not match expected {expected_dim}"
            )

        return embedding

    def get_embedding_and_cropped_image(
        self,
        image_bytes: bytes,
        file_extension: str,
        fallback_mime_type: str,
    ) -> tuple[list[float], bytes | None, str | None, str | None]:
        result = self._predict(image_bytes, file_extension)

        if not isinstance(result, (list, tuple)) or len(result) < 3:
            raise RuntimeError("Embedding API returned an unexpected response format")

        embedding = self._extract_embedding(result[0])
        reported_dim = self._extract_dimension(result[2])

        if len(embedding) != reported_dim:
            raise ValueError(
                f"Embedding length mismatch: len={len(embedding)} but reported_dim={reported_dim}"
            )

        expected_dim = self._settings.qdrant_vector_size
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding dimension {len(embedding)} does not match expected {expected_dim}"
            )

        cropped_bytes, cropped_mime, cropped_ext = self._extract_cropped_image(
            result[1],
            fallback_mime_type=fallback_mime_type,
            fallback_extension=file_extension,
        )

        return embedding, cropped_bytes, cropped_mime, cropped_ext

    def _predict(self, image_bytes: bytes, file_extension: str):
        suffix = f".{file_extension}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_bytes)
            temp_path = tmp.name

        result = None
        last_error: Exception | None = None

        retries = max(1, int(self._settings.embedding_api_max_retries))
        base_delay = max(0.0, float(self._settings.embedding_api_retry_delay_seconds))

        try:
            for attempt in range(1, retries + 1):
                try:
                    result = self._client.predict(
                        img=handle_file(temp_path),
                        api_name=self._settings.embedding_api_name,
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
                    f"Embedding API timed out after {retries} attempt(s)"
                ) from last_error
            raise RuntimeError(f"Embedding API request failed: {last_error}") from last_error

        return result

    @staticmethod
    def _extract_cropped_image(
        raw_crop: object,
        *,
        fallback_mime_type: str,
        fallback_extension: str,
    ) -> tuple[bytes | None, str | None, str | None]:
        if not isinstance(raw_crop, dict):
            return None, None, None

        data: bytes | None = None

        path = raw_crop.get("path")
        if isinstance(path, str) and path and os.path.exists(path):
            with open(path, "rb") as handle:
                data = handle.read()
        elif isinstance(raw_crop.get("url"), str) and raw_crop.get("url"):
            url = raw_crop["url"]
            try:
                with urllib.request.urlopen(url, timeout=15) as response:
                    data = response.read()
            except Exception:
                data = None

        if not data:
            return None, None, None

        mime_type = raw_crop.get("mime_type") if isinstance(raw_crop.get("mime_type"), str) else None
        if not mime_type:
            mime_type = mimetypes.guess_type(path or "")[0]
        if not mime_type:
            mime_type = fallback_mime_type

        extension = None
        if isinstance(path, str) and "." in path:
            extension = path.rsplit(".", 1)[1].lower()
        if not extension:
            guessed_ext = mimetypes.guess_extension(mime_type or "")
            if guessed_ext:
                extension = guessed_ext.lstrip(".").lower()
        if not extension:
            extension = fallback_extension
        if extension == "jpg":
            extension = "jpeg"

        return data, mime_type, extension

    def _extract_embedding(self, raw: object) -> list[float]:
        candidate = raw

        if isinstance(raw, str):
            try:
                candidate = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("Embedding payload string is not valid JSON") from exc

        if isinstance(candidate, dict):
            for key in ("embedding", "vector", "data"):
                if key in candidate:
                    candidate = candidate[key]
                    break

        if not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes, bytearray)):
            raise ValueError("Embedding payload is not a numeric sequence")

        parsed: list[float] = []
        for value in candidate:
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Embedding contains non-numeric values") from exc
            if not math.isfinite(number):
                raise ValueError("Embedding contains non-finite values")
            parsed.append(number)

        if not parsed:
            raise ValueError("Embedding vector is empty")

        return parsed

    @staticmethod
    def _extract_dimension(raw_dim: object) -> int:
        try:
            dim = int(raw_dim)
        except (TypeError, ValueError) as exc:
            raise ValueError("Embedding dimension is not a valid integer") from exc

        if dim <= 0:
            raise ValueError("Embedding dimension must be greater than zero")

        return dim

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
