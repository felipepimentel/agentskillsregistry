"""
Pydantic models for Agent Skills Registry.
Implements Cloudflare Agent Skills Discovery RFC specifications.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
import re


# RFC Naming requirements: 1-64 characters, lowercase alphanumeric and hyphens only
# No leading/trailing or consecutive hyphens
SKILL_NAME_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$')


def validate_skill_name(name: str) -> str:
    """Validate skill name according to RFC specifications."""
    if not name or len(name) > 64:
        raise ValueError("Skill name must be 1-64 characters")
    if not SKILL_NAME_PATTERN.match(name):
        raise ValueError(
            "Skill name must be lowercase alphanumeric with hyphens, "
            "no leading/trailing/consecutive hyphens"
        )
    return name


def normalize_skill_name(name: str) -> str:
    """Convert a human-readable name to RFC-compliant slug."""
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to 64 characters
    if len(slug) > 64:
        slug = slug[:64].rstrip('-')
    return slug


class SkillFile(BaseModel):
    """Represents a file associated with a skill (RFC files array)."""
    path: str = Field(..., description="Relative path to the file from skill directory")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    description: Optional[str] = Field(None, description="Brief description of the file")


class SkillInput(BaseModel):
    """Input schema for registering new skills."""
    name: str = Field(..., description="Human-readable name of the skill")
    description: str = Field(
        ...,
        max_length=1024,
        description="Natural language description of what the skill does (max 1024 chars per RFC)"
    )
    input_schema: Dict[str, Any] = Field(
        ...,
        description="JSON Schema for the input parameters"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema for the output (optional)"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for filtering and categorization")
    version: str = Field(default="1.0.0", description="Semantic version of the skill")
    author: Optional[str] = Field(None, description="Author or organization name")
    documentation: Optional[str] = Field(None, description="Extended documentation in Markdown")
    examples: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Example invocations with input/output pairs"
    )


class Skill(SkillInput):
    """Full skill model with auto-generated fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str = Field(default="", description="RFC-compliant URL-safe identifier")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    files: List[SkillFile] = Field(
        default_factory=lambda: [SkillFile(path="SKILL.md", content_type="text/markdown")]
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = normalize_skill_name(self.name)


class SearchResult(BaseModel):
    """Search result containing a skill and similarity score."""
    skill: Skill
    score: float = Field(..., ge=0, le=1, description="Similarity score (0-1)")


class RegisterResponse(BaseModel):
    """Response model for skill registration."""
    id: str
    slug: str
    message: str


# RFC Well-Known Models

class SkillIndexEntry(BaseModel):
    """Entry in the well-known skills index (RFC index.json)."""
    name: str = Field(..., description="RFC-compliant skill name/slug")
    description: str = Field(..., max_length=1024, description="Brief description")
    files: List[str] = Field(..., description="List of file paths for this skill")


class SkillIndex(BaseModel):
    """RFC-compliant index.json structure."""
    version: str = Field(default="0.1", description="RFC version")
    skills: List[SkillIndexEntry] = Field(default_factory=list)


class SkillMetadata(BaseModel):
    """YAML frontmatter metadata for SKILL.md files."""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


# Discovery Client Models

class RemoteSkillInfo(BaseModel):
    """Information about a skill discovered from a remote server."""
    origin: str = Field(..., description="Origin URL of the skill provider")
    name: str
    description: str
    files: List[str]
    skill_url: str = Field(..., description="Full URL to the skill directory")


class DiscoveryResult(BaseModel):
    """Result of discovering skills from a remote server."""
    origin: str
    skills: List[RemoteSkillInfo]
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# Progressive Disclosure Models

class SkillLevel1(BaseModel):
    """Level 1: Index metadata only (~100 tokens)."""
    name: str
    description: str


class SkillLevel2(BaseModel):
    """Level 2: Full SKILL.md content (~5k tokens max)."""
    name: str
    description: str
    version: str
    author: Optional[str]
    tags: List[str]
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    documentation: Optional[str]
    examples: Optional[List[Dict[str, Any]]]


class SkillLevel3(BaseModel):
    """Level 3: Full skill with all supporting resources."""
    skill: SkillLevel2
    resources: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of file paths to content"
    )
