"""
GeoHarvest Qdrant Vector Database Service (TAS v1.0 §4.1, §4.2, §7.1).

Connects to the Qdrant vector database container for scientific literature,
algorithm specifications, sensor documentation, and geospatial entity retrieval.
"""

import logging
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.vector.qdrant")

DEFAULT_VECTOR_SIZE = 384  # Standard size for lightweight scientific embeddings (e.g. MiniLM / BGE-small / BGE-M3 dense)
COLLECTION_SCIENTIFIC = "scientific_knowledge"
COLLECTION_ALGORITHMS = "geospatial_algorithms"
COLLECTION_SENSORS = "satellite_sensors"


class QdrantVectorService:
    """Manages Qdrant vector database client connection, collections, and semantic search."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.api_key = api_key or settings.qdrant_api_key
        self._client: Optional[QdrantClient] = None

    def get_client(self) -> QdrantClient:
        """Returns or lazily creates a QdrantClient instance."""
        if self._client is None:
            logger.info(f"Connecting to Qdrant vector database at {self.host}:{self.port}...")
            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=10.0,
            )
        return self._client

    def is_available(self) -> bool:
        """Checks if Qdrant service is reachable."""
        try:
            client = self.get_client()
            client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant vector database not available at {self.host}:{self.port}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns health telemetry and collection statistics from Qdrant."""
        try:
            client = self.get_client()
            cols_res = client.get_collections()
            collection_names = [c.name for c in cols_res.collections]

            details = {}
            for name in collection_names:
                info = client.get_collection(collection_name=name)
                details[name] = {
                    "vectors_count": info.points_count,
                    "indexed_vectors_count": info.indexed_vectors_count,
                    "status": str(info.status),
                }

            return {
                "available": True,
                "host": self.host,
                "port": self.port,
                "collections_count": len(collection_names),
                "collections": details,
            }
        except Exception as e:
            return {
                "available": False,
                "host": self.host,
                "port": self.port,
                "error": str(e),
                "collections_count": 0,
                "collections": {},
            }

    def ensure_collections(self, vector_size: int = DEFAULT_VECTOR_SIZE) -> None:
        """Ensures standard GeoHarvest vector collections exist with cosine similarity metric."""
        client = self.get_client()
        existing = {c.name for c in client.get_collections().collections}

        target_collections = [
            COLLECTION_SCIENTIFIC,
            COLLECTION_ALGORITHMS,
            COLLECTION_SENSORS,
        ]

        for coll_name in target_collections:
            if coll_name not in existing:
                logger.info(f"Creating Qdrant collection: {coll_name} (dim={vector_size})")
                client.create_collection(
                    collection_name=coll_name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE
                    )
                )

    def upsert_point(
        self,
        collection_name: str,
        point_id: int | str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """Upserts a single vector with associated metadata payload."""
        try:
            client = self.get_client()
            client.upsert(
                collection_name=collection_name,
                points=[
                    qmodels.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert point to Qdrant collection {collection_name}: {e}")
            return False

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Performs nearest-neighbor semantic vector search in Qdrant."""
        try:
            client = self.get_client()
            hits = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            return [
                {
                    "id": h.id,
                    "score": round(float(h.score), 4),
                    "payload": h.payload
                }
                for h in hits
            ]
        except Exception as e:
            logger.error(f"Qdrant search error on {collection_name}: {e}")
            return []

    def seed_algorithm_knowledge(self) -> int:
        """
        Seeds Qdrant with the verified algorithm registry and sensor knowledge.
        Generates deterministic pseudo-embeddings when an external embedding model is not yet loaded.
        """
        import hashlib
        from backend.core.processing.algorithms import algorithm_registry

        if not self.is_available():
            logger.warning("Cannot seed algorithms: Qdrant service is currently offline.")
            return 0

        self.ensure_collections()
        algos = algorithm_registry.list_all()
        seeded_count = 0

        for idx, algo in enumerate(algos, start=1):
            # Deterministic pseudo-embedding for bootstrap search
            text = f"{algo.name} {algo.category} {algo.scientific_description} {algo.id}"
            hasher = hashlib.sha256(text.encode("utf-8"))
            digest = hasher.digest()
            raw_floats = [((b / 255.0) * 2.0 - 1.0) for b in digest]
            vector = (raw_floats * (DEFAULT_VECTOR_SIZE // len(raw_floats) + 1))[:DEFAULT_VECTOR_SIZE]

            payload = {
                "id": algo.id,
                "name": algo.name,
                "category": algo.category,
                "scientific_description": algo.scientific_description,
                "formula": algo.mathematical_formula,
                "citations": algo.scientific_citations,
                "inputs": [i.model_dump() for i in algo.inputs],
            }

            if self.upsert_point(COLLECTION_ALGORITHMS, idx, vector, payload):
                seeded_count += 1

        logger.info(f"Seeded {seeded_count} scientific algorithms into Qdrant vector database.")
        return seeded_count


# Global singleton instance
qdrant_service = QdrantVectorService()
