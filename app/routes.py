from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.schemas import (
    DeletePointResponse,
    EnrollResponse,
    HealthResponse,
    MatchItem,
    PointResponse,
    SearchResponse,
    VoiceEnrollResponse,
    VoiceMatchItem,
    VoiceSearchResponse,
)
from app.utils.validators import validate_audio_upload, validate_image_upload

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(status="ok", collection=settings.qdrant_collection_name)


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(
    request: Request,
    name: str = Form(...),
    user_id: str | None = Form(default=None),
    image: UploadFile = File(...),
) -> EnrollResponse:
    settings = request.app.state.settings
    qdrant_service = request.app.state.qdrant_service
    storage_service = request.app.state.storage_service
    embedding_service = request.app.state.embedding_service

    image_bytes = await image.read()
    extension = validate_image_upload(
        image,
        image_bytes,
        allowed_types=settings.allowed_image_type_set,
        max_size_bytes=settings.max_image_size_bytes,
    )

    resolved_user_id = user_id or str(uuid4())
    point_id = str(uuid4())
    content_type = image.content_type or "application/octet-stream"

    uploaded_key: str | None = None
    image_url: str | None = None

    try:
        embedding, cropped_bytes, cropped_mime, cropped_ext = embedding_service.get_embedding_and_cropped_image(
            image_bytes,
            extension,
            content_type,
        )

        upload_bytes = cropped_bytes if cropped_bytes else image_bytes
        upload_mime = cropped_mime if cropped_mime else content_type
        upload_ext = cropped_ext if cropped_ext else extension

        uploaded_key, image_url = storage_service.upload_image(
            image_bytes=upload_bytes,
            user_id=resolved_user_id,
            extension=upload_ext,
            mime_type=upload_mime,
        )

        qdrant_service.upsert_point(
            point_id=point_id,
            vector=embedding,
            payload={
                "user_id": resolved_user_id,
                "name": name,
                "image_url": image_url,
            },
        )
    except HTTPException:
        raise
    except ValueError as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TimeoutError as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Enroll failed: {exc}",
        ) from exc
    except Exception as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Enroll failed: {exc}",
        ) from exc

    return EnrollResponse(
        point_id=point_id,
        user_id=resolved_user_id,
        name=name,
        image_url=image_url,
        collection=settings.qdrant_collection_name,
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    request: Request,
    image: UploadFile = File(...),
    top_k: int | None = Form(default=None),
) -> SearchResponse:
    settings = request.app.state.settings
    qdrant_service = request.app.state.qdrant_service
    embedding_service = request.app.state.embedding_service

    if top_k is not None and top_k != settings.fixed_top_k:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"top_k is fixed to {settings.fixed_top_k}",
        )

    image_bytes = await image.read()
    extension = validate_image_upload(
        image,
        image_bytes,
        allowed_types=settings.allowed_image_type_set,
        max_size_bytes=settings.max_image_size_bytes,
    )

    try:
        query_embedding = embedding_service.get_embedding(image_bytes, extension)
        points = qdrant_service.search_points(
            query_embedding,
            limit=settings.fixed_top_k,
            min_score=settings.min_match_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Search failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search failed: {exc}",
        ) from exc

    matches = []
    for point in points:
        score = float(point.score)

        payload = point.payload or {}
        matches.append(
            MatchItem(
                point_id=str(point.id),
                score=score,
                user_id=payload.get("user_id"),
                name=payload.get("name"),
                image_url=payload.get("image_url"),
            )
        )

    matches.sort(key=lambda item: item.score, reverse=True)

    return SearchResponse(top_k=settings.fixed_top_k, matches=matches)


@router.post("/voice/enroll", response_model=VoiceEnrollResponse)
async def enroll_voice(
    request: Request,
    name: str = Form(...),
    user_id: str | None = Form(default=None),
    audio: UploadFile = File(...),
) -> VoiceEnrollResponse:
    settings = request.app.state.settings
    qdrant_service = request.app.state.voice_qdrant_service
    storage_service = request.app.state.storage_service
    embedding_service = request.app.state.voice_embedding_service

    audio_bytes = await audio.read()
    extension = validate_audio_upload(
        audio,
        audio_bytes,
        allowed_types=settings.allowed_audio_type_set,
        max_size_bytes=settings.max_audio_size_bytes,
    )

    resolved_user_id = user_id or str(uuid4())
    point_id = str(uuid4())
    content_type = audio.content_type or "application/octet-stream"

    uploaded_key: str | None = None
    audio_url: str | None = None

    try:
        embedding = embedding_service.get_embedding(audio_bytes, extension)
        uploaded_key, audio_url = storage_service.upload_audio(
            audio_bytes=audio_bytes,
            user_id=resolved_user_id,
            extension=extension,
            mime_type=content_type,
        )

        qdrant_service.upsert_point(
            point_id=point_id,
            vector=embedding,
            payload={
                "user_id": resolved_user_id,
                "name": name,
                "audio_url": audio_url,
            },
        )
    except HTTPException:
        raise
    except ValueError as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TimeoutError as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Voice enroll failed: {exc}",
        ) from exc
    except Exception as exc:
        if uploaded_key:
            storage_service.delete_image_by_key(uploaded_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Voice enroll failed: {exc}",
        ) from exc

    return VoiceEnrollResponse(
        point_id=point_id,
        user_id=resolved_user_id,
        name=name,
        audio_url=audio_url,
        collection=settings.voice_qdrant_collection_name,
    )


@router.post("/voice/search", response_model=VoiceSearchResponse)
async def search_voice(
    request: Request,
    audio: UploadFile = File(...),
    top_k: int | None = Form(default=None),
) -> VoiceSearchResponse:
    settings = request.app.state.settings
    qdrant_service = request.app.state.voice_qdrant_service
    embedding_service = request.app.state.voice_embedding_service

    if top_k is not None and top_k != settings.fixed_top_k:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"top_k is fixed to {settings.fixed_top_k}",
        )

    audio_bytes = await audio.read()
    extension = validate_audio_upload(
        audio,
        audio_bytes,
        allowed_types=settings.allowed_audio_type_set,
        max_size_bytes=settings.max_audio_size_bytes,
    )

    try:
        query_embedding = embedding_service.get_embedding(audio_bytes, extension)
        points = qdrant_service.search_points(
            query_embedding,
            limit=settings.fixed_top_k,
            min_score=settings.min_voice_match_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Voice search failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Voice search failed: {exc}",
        ) from exc

    matches = []
    for point in points:
        score = float(point.score)

        payload = point.payload or {}
        matches.append(
            VoiceMatchItem(
                point_id=str(point.id),
                score=score,
                user_id=payload.get("user_id"),
                name=payload.get("name"),
                audio_url=payload.get("audio_url"),
            )
        )

    matches.sort(key=lambda item: item.score, reverse=True)

    return VoiceSearchResponse(top_k=settings.fixed_top_k, matches=matches)


@router.get("/point/{point_id}", response_model=PointResponse)
def get_point(request: Request, point_id: str) -> PointResponse:
    settings = request.app.state.settings
    qdrant_service = request.app.state.qdrant_service

    try:
        point = qdrant_service.get_point(point_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch point: {exc}",
        ) from exc

    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point not found")

    payload = point.payload or {}
    return PointResponse(
        point_id=str(point.id),
        user_id=payload.get("user_id"),
        name=payload.get("name"),
        image_url=payload.get("image_url"),
        collection=settings.qdrant_collection_name,
    )


@router.delete("/point/{point_id}", response_model=DeletePointResponse)
def delete_point(request: Request, point_id: str) -> DeletePointResponse:
    qdrant_service = request.app.state.qdrant_service
    storage_service = request.app.state.storage_service

    try:
        point = qdrant_service.get_point(point_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch point before deletion: {exc}",
        ) from exc

    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point not found")

    payload = point.payload or {}
    image_url = payload.get("image_url")

    deleted_from_qdrant = False
    deleted_from_storage = False

    try:
        qdrant_service.delete_point(point_id)
        deleted_from_qdrant = True

        if image_url:
            deleted_from_storage = storage_service.delete_image_by_url(image_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Delete failed: {exc}",
        ) from exc

    return DeletePointResponse(
        point_id=point_id,
        deleted_from_qdrant=deleted_from_qdrant,
        deleted_from_storage=deleted_from_storage,
    )
