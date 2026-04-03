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
