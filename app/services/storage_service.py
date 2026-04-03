import uuid
from urllib.parse import urlparse

import boto3

from app.config import Settings


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bucket = settings.supabase_bucket
        self._public_prefix = self._get_public_prefix()

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.supabase_s3_endpoint,
            aws_access_key_id=settings.supabase_access_key,
            aws_secret_access_key=settings.supabase_secret_key,
            region_name=settings.supabase_region,
        )

    def upload_image(self, image_bytes: bytes, user_id: str, extension: str, mime_type: str) -> tuple[str, str]:
        key = f"faces/{user_id}/{uuid.uuid4().hex}.{extension}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=image_bytes,
            ContentType=mime_type,
        )
        return key, f"{self._public_prefix}/{key}"

    def delete_image_by_url(self, image_url: str) -> bool:
        key = self._extract_key(image_url)
        self._client.delete_object(Bucket=self._bucket, Key=key)
        return True

    def delete_image_by_key(self, key: str) -> bool:
        self._client.delete_object(Bucket=self._bucket, Key=key)
        return True

    def _get_public_prefix(self) -> str:
        if self._settings.supabase_public_base_url:
            base = self._settings.supabase_public_base_url.rstrip("/")
            return f"{base}/{self._bucket}"

        endpoint = self._settings.supabase_s3_endpoint.rstrip("/")
        parsed = urlparse(endpoint)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("SUPABASE_S3_ENDPOINT must be a valid URL")

        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}/storage/v1/object/public/{self._bucket}"

    def _extract_key(self, image_url: str) -> str:
        prefix = f"{self._public_prefix}/"
        if image_url.startswith(prefix):
            return image_url[len(prefix) :]

        parsed = urlparse(image_url)
        path = parsed.path.lstrip("/")
        expected = f"storage/v1/object/public/{self._bucket}/"
        if expected in path:
            return path.split(expected, 1)[1]

        if path.startswith(f"{self._bucket}/"):
            return path.split(f"{self._bucket}/", 1)[1]

        raise ValueError("Unable to determine storage object key from image URL")
