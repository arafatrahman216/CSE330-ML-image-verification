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
