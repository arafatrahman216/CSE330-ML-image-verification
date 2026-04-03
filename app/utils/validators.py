import imghdr

from fastapi import HTTPException, UploadFile, status


def validate_image_upload(
    upload_file: UploadFile,
    image_bytes: bytes,
    *,
    allowed_types: set[str],
    max_size_bytes: int,
) -> str:
    mime_type = (upload_file.content_type or "").lower()
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {mime_type or 'unknown'}",
        )

    size = len(image_bytes)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds max size of {max_size_bytes} bytes",
        )

    detected = imghdr.what(None, h=image_bytes)
    if detected not in {"jpeg", "png", "webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image content. Only jpeg/png/webp are allowed",
        )

    filename = upload_file.filename or "upload"
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
    else:
        ext = detected

    if ext == "jpg":
        ext = "jpeg"

    if ext not in {"jpeg", "png", "webp"}:
        ext = detected

    return ext


def validate_audio_upload(
    upload_file: UploadFile,
    audio_bytes: bytes,
    *,
    allowed_types: set[str],
    max_size_bytes: int,
) -> str:
    filename = upload_file.filename or "upload"
    ext = ""
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()

    extension_to_mime = {
        "wav": {"audio/wav", "audio/x-wav"},
        "mp3": {"audio/mpeg", "audio/mp3"},
        "flac": {"audio/flac", "audio/x-flac"},
        "webm": {"audio/webm"},
    }

    size = len(audio_bytes)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")
    if size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio exceeds max size of {max_size_bytes} bytes",
        )

    mime_type = (upload_file.content_type or "").lower()
    if mime_type in {"", "application/octet-stream"} and ext in extension_to_mime:
        mime_type = sorted(extension_to_mime[ext])[0]

    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio type: {mime_type or 'unknown'}",
        )

    if ext in extension_to_mime and mime_type not in extension_to_mime[ext]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file extension does not match content type",
        )

    if ext not in extension_to_mime:
        mime_to_ext = {
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/flac": "flac",
            "audio/x-flac": "flac",
            "audio/webm": "webm",
        }
        ext = mime_to_ext.get(mime_type, "wav")

    return ext
