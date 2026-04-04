# Voice Identification API

This file documents the backend endpoints added for voice-based identification.

## Base URL

- Local: `http://127.0.0.1:8000`

## Endpoints

### 1) Enroll Voice

- Method: `POST`
- Path: `/voice/enroll`
- Content-Type: `multipart/form-data`

Form fields:
- `name` (required, string): Person name.
- `user_id` (optional, string): If not provided, backend generates UUID.
- `audio` (required, file): Supported content types are controlled by `ALLOWED_AUDIO_TYPES`.

What it does:
- Validates upload type and size.
- Sends uploaded voice to speaker embedding API.
- Uploads audio file to Supabase storage under `voices/<user_id>/...`.
- Saves embedding + payload (`user_id`, `name`, `audio_url`) into voice Qdrant collection.

Success response example:

```json
{
  "point_id": "6fc4d4a7-f2f1-4f84-89b3-f6d0e39d9349",
  "user_id": "u-001",
  "name": "Jane Doe",
  "audio_url": "https://<project>.supabase.co/storage/v1/object/public/<bucket>/voices/u-001/<file>.wav",
  "collection": "voice"
}
```

### 2) Search Voice (Identify)

- Method: `POST`
- Path: `/voice/search`
- Content-Type: `multipart/form-data`

Form fields:
- `audio` (required, file): Query voice file.
- `top_k` (optional, int): Must match fixed value from `FIXED_TOP_K` if provided.

What it does:
- Validates upload type and size.
- Generates query embedding from uploaded voice.
- Searches in voice Qdrant collection.
- Returns top matches sorted by score descending.

Success response example:

```json
{
  "top_k": 5,
  "matches": [
    {
      "point_id": "6fc4d4a7-f2f1-4f84-89b3-f6d0e39d9349",
      "score": 0.912,
      "user_id": "u-001",
      "name": "Jane Doe",
      "audio_url": "https://<project>.supabase.co/storage/v1/object/public/<bucket>/voices/u-001/<file>.wav"
    }
  ]
}
```

## Required Environment Variables for Voice Flow

- `VOICE_QDRANT_COLLECTION_NAME` (default: `voice`)
- `VOICE_QDRANT_VECTOR_SIZE` (default: `256`)
- `VOICE_QDRANT_DISTANCE_METRIC` (default: `cosine`)
- `VOICE_EMBEDDING_API_URL` (default: `enayetalvee/speaker-embedding-resnet34`)
- `VOICE_EMBEDDING_API_NAME` (default: `/predict`)
- `VOICE_EMBEDDING_API_INPUT_NAME` (default: `audio`)
- `VOICE_EMBEDDING_API_MAX_RETRIES` (default: `3`)
- `VOICE_EMBEDDING_API_RETRY_DELAY_SECONDS` (default: `1.5`)
- `ALLOWED_AUDIO_TYPES`
- `MAX_AUDIO_SIZE_MB`
- `MIN_VOICE_MATCH_SCORE`

## cURL Examples

Enroll:

```bash
curl -X POST "http://127.0.0.1:8000/voice/enroll" \
  -F "name=Jane Doe" \
  -F "user_id=u-001" \
  -F "audio=@/absolute/path/to/sample.wav"
```

Search:

```bash
curl -X POST "http://127.0.0.1:8000/voice/search" \
  -F "audio=@/absolute/path/to/query.wav" \
  -F "top_k=5"
```

## Notes

- The existing face APIs are unchanged.
- Voice embeddings are stored in a dedicated Qdrant collection to avoid mixing with face vectors.
- If your target Space uses a different API input key or api_name, adjust:
  - `VOICE_EMBEDDING_API_INPUT_NAME`
  - `VOICE_EMBEDDING_API_NAME`
