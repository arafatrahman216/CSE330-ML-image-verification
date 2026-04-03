from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import Settings


DISTANCE_MAP = {
    "cosine": models.Distance.COSINE,
    "dot": models.Distance.DOT,
    "euclid": models.Distance.EUCLID,
}


class VoiceQdrantService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collection = settings.voice_qdrant_collection_name
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    def ensure_collection_exists(self) -> None:
        if self._client.collection_exists(self._collection):
            return

        metric = self._settings.voice_qdrant_distance_metric.lower()
        if metric not in DISTANCE_MAP:
            raise ValueError(
                f"Unsupported voice Qdrant metric: {self._settings.voice_qdrant_distance_metric}"
            )

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=models.VectorParams(
                size=self._settings.voice_qdrant_vector_size,
                distance=DISTANCE_MAP[metric],
            ),
        )

    def upsert_point(self, point_id: str, vector: list[float], payload: dict) -> None:
        point = models.PointStruct(id=point_id, vector=vector, payload=payload)
        self._client.upsert(collection_name=self._collection, points=[point], wait=True)

    def search_points(
        self,
        vector: list[float],
        limit: int,
        min_score: float | None = None,
    ) -> list[models.ScoredPoint]:
        return self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=limit,
            score_threshold=min_score,
            with_payload=True,
            with_vectors=False,
        )

    def get_point(self, point_id: str):
        points = self._client.retrieve(
            collection_name=self._collection,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        return points[0] if points else None

    def delete_point(self, point_id: str) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=models.PointIdsList(points=[point_id]),
            wait=True,
        )
