# Face Identification Backend (FastAPI + Qdrant + Supabase S3)

A modular FastAPI backend for face enrollment and search.

## Features

- Uses Qdrant Cloud as the only database (`image` collection)
- Stores payload fields in Qdrant: `user_id`, `name`, `image_url`
- Uploads image files to Supabase Storage (S3-compatible endpoint)
- Calls external embedding API (`/get_embedding`) via `gradio_client`
- Validates image type and size
- Validates embedding dimension before insert/search
- Creates Qdrant collection automatically on startup if missing

## Project Structure

```text
backend-image/
  main.py
  app/
    config.py
    routes.py
    schemas.py
    services/
      embedding_service.py
      qdrant_service.py
      storage_service.py
    utils/
      validators.py
  .env.example
  requirements.txt
```

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd backend-image
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy and edit environment variables:

```bash
cp .env.example .env
```

3. Start server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `GET /health`
- `POST /enroll`
- `POST /search`
- `GET /point/{point_id}`
- `DELETE /point/{point_id}`

## cURL Examples

Enroll a person:

```bash
curl -X POST "http://127.0.0.1:8000/enroll" \
  -F "name=John Doe" \
  -F "user_id=user-123" \
  -F "image=@/absolute/path/to/person.jpg"
```

Search a person:

```bash
curl -X POST "http://127.0.0.1:8000/search" \
  -F "image=@/absolute/path/to/query.jpg" \
  -F "top_k=5"
```

Get a point:

```bash
curl "http://127.0.0.1:8000/point/<point_id>"
```

Delete a point:

```bash
curl -X DELETE "http://127.0.0.1:8000/point/<point_id>"
```

## Notes

- `top_k` is fixed to `5` by design.
- If `user_id` is omitted during enroll, a UUID is generated.
- On delete, backend removes both Qdrant point and the linked Supabase object.
