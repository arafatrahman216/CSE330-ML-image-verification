from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    collection: str


class EnrollResponse(BaseModel):
    point_id: str
    user_id: str
    name: str
    image_url: str
    collection: str


class MatchItem(BaseModel):
    point_id: str
    score: float
    user_id: str | None = None
    name: str | None = None
    image_url: str | None = None


class SearchResponse(BaseModel):
    top_k: int
    matches: list[MatchItem] = Field(default_factory=list)


class PointResponse(BaseModel):
    point_id: str
    user_id: str | None = None
    name: str | None = None
    image_url: str | None = None
    collection: str


class DeletePointResponse(BaseModel):
    point_id: str
    deleted_from_qdrant: bool
    deleted_from_storage: bool


class VoiceEnrollResponse(BaseModel):
    point_id: str
    user_id: str
    name: str
    audio_url: str
    collection: str


class VoiceMatchItem(BaseModel):
    point_id: str
    score: float
    user_id: str | None = None
    name: str | None = None
    audio_url: str | None = None


class VoiceSearchResponse(BaseModel):
    top_k: int
    matched: bool
    status: str
    matches: list[VoiceMatchItem] = Field(default_factory=list)


class FaceVoiceCandidate(BaseModel):
    user_id: str
    name: str | None = None
    face_score: float
    voice_score: float
    combined_score: float


class FaceVoiceSearchResponse(BaseModel):
    top_k: int
    matched: bool
    status: str
    best_match: FaceVoiceCandidate | None = None
    candidates: list[FaceVoiceCandidate] = Field(default_factory=list)
    face_matches: list[MatchItem] = Field(default_factory=list)
    voice_matches: list[VoiceMatchItem] = Field(default_factory=list)
