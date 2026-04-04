from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import router
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.storage_service import StorageService
from app.services.voice_embedding_service import VoiceEmbeddingService
from app.services.voice_qdrant_service import VoiceQdrantService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    qdrant_service = QdrantService(settings)
    qdrant_service.ensure_collection_exists()

    voice_qdrant_service = VoiceQdrantService(settings)
    voice_qdrant_service.ensure_collection_exists()

    storage_service = StorageService(settings)
    embedding_service = EmbeddingService(settings)
    voice_embedding_service = VoiceEmbeddingService(settings)

    app.state.settings = settings
    app.state.qdrant_service = qdrant_service
    app.state.storage_service = storage_service
    app.state.embedding_service = embedding_service
    app.state.voice_qdrant_service = voice_qdrant_service
    app.state.voice_embedding_service = voice_embedding_service

    yield


app = FastAPI(title="Face ID Backend", version="1.0.0", lifespan=lifespan)
settings = get_settings()
allow_all_origins = "*" in settings.cors_allowed_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else settings.cors_allowed_origin_list,
    allow_credentials=False if allow_all_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
