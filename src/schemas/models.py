from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid

class SkillInput(BaseModel):
    name: str = Field(..., description="Unique name of the skill")
    description: str = Field(..., description="Natural language description of what the skill does")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for the input parameters")
    tags: List[str] = Field(default_factory=list, description="Optional tags for filtering")

class Skill(SkillInput):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=str) # simplified timestamp

class SearchResult(BaseModel):
    skill: Skill
    score: float = Field(..., description="Similarity score (0-1)")

class RegisterResponse(BaseModel):
    id: str
    message: str
