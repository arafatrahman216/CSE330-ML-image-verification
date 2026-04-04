from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Face ID Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_allowed_origins: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        alias="CORS_ALLOWED_ORIGINS",
    )

    qdrant_url: str = Field(..., alias="QDRANT_URL")
    qdrant_api_key: str = Field(..., alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field("image", alias="QDRANT_COLLECTION_NAME")
    qdrant_vector_size: int = Field(512, alias="QDRANT_VECTOR_SIZE")
    qdrant_distance_metric: str = Field("cosine", alias="QDRANT_DISTANCE_METRIC")

    voice_qdrant_collection_name: str = Field("voice", alias="VOICE_QDRANT_COLLECTION_NAME")
    voice_qdrant_vector_size: int = Field(256, alias="VOICE_QDRANT_VECTOR_SIZE")
    voice_qdrant_distance_metric: str = Field("cosine", alias="VOICE_QDRANT_DISTANCE_METRIC")

    supabase_s3_endpoint: str = Field(..., alias="SUPABASE_S3_ENDPOINT")
    supabase_bucket: str = Field(..., alias="SUPABASE_BUCKET")
    supabase_access_key: str = Field(..., alias="SUPABASE_ACCESS_KEY")
    supabase_secret_key: str = Field(..., alias="SUPABASE_SECRET_KEY")
    supabase_region: str = Field("us-east-1", alias="SUPABASE_S3_REGION")
    supabase_public_base_url: str | None = Field(None, alias="SUPABASE_PUBLIC_BASE_URL")

    embedding_api_url: str = Field(..., alias="EMBEDDING_API_URL")
    embedding_api_key: str | None = Field(None, alias="EMBEDDING_API_KEY")
    embedding_api_name: str = Field("/get_embedding", alias="EMBEDDING_API_NAME")
    embedding_api_max_retries: int = Field(3, alias="EMBEDDING_API_MAX_RETRIES")
    embedding_api_retry_delay_seconds: float = Field(1.5, alias="EMBEDDING_API_RETRY_DELAY_SECONDS")

    voice_embedding_api_url: str = Field(
        "enayetalvee/speaker-embedding-resnet34",
        alias="VOICE_EMBEDDING_API_URL",
    )
    voice_embedding_api_key: str | None = Field(None, alias="VOICE_EMBEDDING_API_KEY")
    voice_embedding_api_name: str = Field("/predict", alias="VOICE_EMBEDDING_API_NAME")
    voice_embedding_api_input_name: str = Field("audio", alias="VOICE_EMBEDDING_API_INPUT_NAME")
    voice_embedding_api_max_retries: int = Field(3, alias="VOICE_EMBEDDING_API_MAX_RETRIES")
    voice_embedding_api_retry_delay_seconds: float = Field(
        1.5,
        alias="VOICE_EMBEDDING_API_RETRY_DELAY_SECONDS",
    )

    allowed_image_types: str = Field(
        "image/jpeg,image/png,image/webp", alias="ALLOWED_IMAGE_TYPES"
    )
    max_image_size_mb: int = Field(10, alias="MAX_IMAGE_SIZE_MB")
    allowed_audio_types: str = Field(
        "audio/wav,audio/x-wav,audio/mpeg,audio/mp3,audio/flac,audio/x-flac,audio/webm",
        alias="ALLOWED_AUDIO_TYPES",
    )
    max_audio_size_mb: int = Field(20, alias="MAX_AUDIO_SIZE_MB")
    fixed_top_k: int = Field(5, alias="FIXED_TOP_K")
    min_match_score: float = Field(0.4, alias="MIN_MATCH_SCORE")
    min_voice_match_score: float = Field(0.4, alias="MIN_VOICE_MATCH_SCORE")

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def max_audio_size_bytes(self) -> int:
        return self.max_audio_size_mb * 1024 * 1024

    @property
    def allowed_image_type_set(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_image_types.split(",") if item.strip()}

    @property
    def allowed_audio_type_set(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_audio_types.split(",") if item.strip()}

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
