from fastapi import FastAPI, HTTPException, Depends
from typing import List
from src.schemas.models import Skill, SearchResult, RegisterResponse, SkillInput
from src.services.registry import RegistryService
from src.services.embedding import EmbeddingService
from src.services.vector_store import VectorStore

app = FastAPI(title="Agent Skills Registry", version="0.1.0")

# Dependency Injection using a global singleton pattern for simplicity in this MVP
# Ideally use a proper DI container
class ServiceContainer:
    registry = RegistryService()
    embedding = EmbeddingService()
    vector_store = VectorStore(embedding)

services = ServiceContainer()

@app.post("/skills", response_model=RegisterResponse)
async def register_skill(skill_input: SkillInput):
    # create full skill object with ID and timestamp
    skill = Skill(**skill_input.dict())
    
    # 1. Save to Registry (JSON)
    saved_skill = services.registry.register_skill(skill)
    
    # 2. Index in Vector Store
    services.vector_store.add_skill(saved_skill)
    
    return RegisterResponse(id=saved_skill.id, message="Skill registered and indexed successfully")

@app.get("/skills", response_model=List[Skill])
async def list_skills():
    return services.registry.list_skills()

@app.get("/search", response_model=List[SearchResult])
async def search_skills(q: str, limit: int = 5):
    # 1. Search Vector Store for IDs
    results = services.vector_store.search_ids(q, limit=limit)
    
    search_results = []
    for skill_id, distance in results:
        # 2. Hydrate from Registry
        skill = services.registry.get_skill(skill_id)
        if skill:
            # Distance is usually smaller = better, assuming L2 or Cosine distance.
            # Convert to a similarity score if needed. For now just return raw distance or 1/(1+dist).
            score = 1 / (1 + distance) 
            search_results.append(SearchResult(skill=skill, score=score))
            
    return search_results
