import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny

class VectorDBHelper:
    """Abstraction layer for Vector Database operations.
    
    Default implementation uses Qdrant. Can be extended to support others.
    """
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        # Allow overriding via environment variables
        self.host = os.getenv("QDRANT_HOST", host)
        self.port = int(os.getenv("QDRANT_PORT", port))
        
        # Initialize client
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            self._ensure_collections_exist()
        except Exception as e:
            print(f"Warning: Could not connect to Qdrant at {self.host}:{self.port}. Error: {e}")
            self.client = None

    def _ensure_collections_exist(self):
        """Creates required collections if they don't already exist."""
        if not self.client:
            return
            
        collections = ["articles", "telegram_messages"]
        vector_size = 512 # DistilUSE embedding dimension
        
        for collection_name in collections:
            try:
                collection_info = self.client.get_collection(collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
                print(f"Created collection '{collection_name}' in Qdrant.")

    def _generate_uuid(self, string_id: str) -> str:
        """Qdrant requires UUIDs or integers for point IDs. 
        This deterministically converts a string ID to a UUID."""
        return str(uuid.uuid5(uuid.NAMESPACE_OID, str(string_id)))

    def upsert_article(self, article_id: str, embedding: List[float], payload: Dict[str, Any]) -> bool:
        """Insert or update an article in the VDB.
        
        Payload should include: title, source_name, category, language, 
        cluster_id, timestamp, summary_text, image_url, video_url
        """
        if not self.client:
            print("VDB not connected. Skipping upsert.")
            return False
            
        point_id = self._generate_uuid(article_id)
        
        # Ensure ID is in payload for easy retrieval
        payload_with_id = payload.copy()
        payload_with_id["original_id"] = article_id
        
        try:
            self.client.upsert(
                collection_name="articles",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload_with_id
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"Error upserting article {article_id}: {e}")
            return False

    def upsert_telegram_message(self, message_id: str, embedding: List[float], payload: Dict[str, Any]) -> bool:
        """Insert or update a Telegram message in the VDB.
        
        Payload should include: message_id, channel, text, label, 
        match_cluster_id, similarity_score, timestamp
        """
        if not self.client:
            print("VDB not connected. Skipping upsert.")
            return False
            
        point_id = self._generate_uuid(f"tg_{message_id}")
        
        # Ensure ID is in payload for easy retrieval
        payload_with_id = payload.copy()
        payload_with_id["original_id"] = str(message_id)
        
        try:
            self.client.upsert(
                collection_name="telegram_messages",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload_with_id
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"Error upserting telegram message {message_id}: {e}")
            return False

    def search_similar(self, query_embedding: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None, preferred_sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find similar articles using vector search, with optional metadata filters and source preferences."""
        if not self.client:
            return []
            
        conditions = []
        if filters:
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
        
        # Add preferred sources filter using MatchAny
        if preferred_sources:
            conditions.append(
                FieldCondition(key="source_name", match=MatchAny(any=preferred_sources))
            )
            
        query_filter = Filter(must=conditions) if conditions else None
            
        try:
            results = self.client.query_points(
                collection_name="articles",
                query=query_embedding,
                query_filter=query_filter,
                limit=top_k
            )
            
            return [
                {
                    "id": hit.payload.get("original_id", str(hit.id)),
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results.points
            ]
        except Exception as e:
            print(f"Error searching similar articles: {e}")
            return []

    def get_by_cluster(self, cluster_id: str, preferred_sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retrieve all articles belonging to a specific cluster, optionally filtered by sources."""
        if not self.client:
            return []
            
        must_conditions = [FieldCondition(key="cluster_id", match=MatchValue(value=str(cluster_id)))]
        if preferred_sources:
            must_conditions.append(FieldCondition(key="source_name", match=MatchAny(any=preferred_sources)))
            
        try:
            # Qdrant scroll API is better for fetching all by filter
            results, _ = self.client.scroll(
                collection_name="articles",
                scroll_filter=Filter(must=must_conditions),
                limit=1000 # Reasonable upper bound for a single cluster
            )
            
            return [
                {
                    "id": hit.payload.get("original_id", str(hit.id)),
                    "payload": hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            print(f"Error getting cluster {cluster_id}: {e}")
            return []

    def get_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific article by its original ID."""
        if not self.client:
            return None
            
        point_id = self._generate_uuid(article_id)
        
        try:
            results = self.client.retrieve(
                collection_name="articles",
                ids=[point_id]
            )
            
            if results:
                hit = results[0]
                return {
                    "id": hit.payload.get("original_id", str(hit.id)),
                    "payload": hit.payload
                }
            return None
        except Exception as e:
            print(f"Error getting article {article_id}: {e}")
            return None
