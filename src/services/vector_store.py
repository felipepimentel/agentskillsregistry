import chromadb
from chromadb.config import Settings
from typing import List
from src.schemas.models import Skill, SearchResult
from src.services.embedding import EmbeddingService

class VectorStore:
    def __init__(self, embedding_service: EmbeddingService, persist_path: str = "data/chroma"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.embedding_service = embedding_service
        self.collection = self.client.get_or_create_collection(name="skills")

    def add_skill(self, skill: Skill):
        # Embed the description and name
        text_to_embed = f"{skill.name}: {skill.description} Tags: {', '.join(skill.tags)}"
        vector = self.embedding_service.embed_text(text_to_embed)
        
        self.collection.add(
            documents=[text_to_embed],
            embeddings=[vector],
            metadatas=[{"name": skill.name, "tags": ",".join(skill.tags)}],
            ids=[skill.id]
        )

    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        vector = self.embedding_service.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=limit
        )
        
        # Parse results back to SearchResult objects
        # Note: Chroma returns lists of lists
        search_results = []
        if results["ids"]:
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [0]*len(ids)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}]*len(ids)
            
            for i, skill_id in enumerate(ids):
                # We need to fetch the full skill details separately or trust the metadata
                # ideally we fetch from RegistryService using ID.
                # For now, let's create a partial skill object or wrapper
                # We will handle the full hydration in the Discovery Service/API layer
                # Here we just return the ID and score
                pass 
                
        return results # Returning raw chroma results for now, caller handles hydration

    def search_ids(self, query: str, limit: int = 5) -> List[tuple[str, float]]:
        """Returns list of (id, distance)"""
        vector = self.embedding_service.embed_text(query)
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=limit
        )
        
        output = []
        if results["ids"]:
            ids = results["ids"][0]
            distances = results["distances"][0]
            for id, dist in zip(ids, distances):
                output.append((id, dist))
        return output
