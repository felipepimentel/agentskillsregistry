"""
Agent Skills Registry API.
Implements Cloudflare Agent Skills Discovery RFC with well-known endpoints.
"""
from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import List, Optional
from src.schemas.models import (
    Skill, SearchResult, RegisterResponse, SkillInput,
    SkillIndex, SkillIndexEntry, SkillLevel1, SkillLevel2, SkillLevel3,
    DiscoveryResult, RemoteSkillInfo
)
from src.services.registry import RegistryService
from src.services.embedding import EmbeddingService
from src.services.vector_store import VectorStore
from src.services.skill_renderer import SkillRenderer
from src.services.discovery import DiscoveryClient, DiscoveryService


app = FastAPI(
    title="Agent Skills Registry",
    version="1.0.0",
    description="RFC-compliant Agent Skills Discovery Registry"
)


class ServiceContainer:
    """Dependency injection container for services."""
    registry = RegistryService()
    embedding = EmbeddingService()
    vector_store = VectorStore(embedding)
    renderer = SkillRenderer()
    discovery = DiscoveryService()


services = ServiceContainer()


# =============================================================================
# RFC Well-Known Endpoints (/.well-known/skills/)
# =============================================================================

@app.get(
    "/.well-known/skills/index.json",
    response_model=SkillIndex,
    tags=["RFC Well-Known"],
    summary="Get skills index (RFC index.json)"
)
async def get_skills_index(response: Response):
    """
    Returns the RFC-compliant index.json listing all available skills.
    This is the entry point for skill discovery (Level 1).
    """
    skills = services.registry.list_skills()
    index = services.renderer.render_index_json(skills)

    # RFC-compliant headers
    response.headers["Content-Type"] = "application/json"
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes

    return index


@app.get(
    "/.well-known/skills/{skill_name}/SKILL.md",
    response_class=PlainTextResponse,
    tags=["RFC Well-Known"],
    summary="Get skill definition (RFC SKILL.md)"
)
async def get_skill_md(skill_name: str, response: Response):
    """
    Returns the SKILL.md file for a specific skill (Level 2).
    Contains YAML frontmatter with metadata and Markdown documentation.
    """
    skill = services.registry.get_skill_by_slug(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    content = services.renderer.render_skill_md(skill)

    # RFC-compliant headers
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=300"

    return content


@app.get(
    "/.well-known/skills/{skill_name}/{file_path:path}",
    response_class=PlainTextResponse,
    tags=["RFC Well-Known"],
    summary="Get skill resource file (Level 3)"
)
async def get_skill_resource(skill_name: str, file_path: str, response: Response):
    """
    Returns an additional resource file for a skill (Level 3).
    Supports scripts, references, and other supporting files.
    """
    skill = services.registry.get_skill_by_slug(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    content = services.renderer.read_skill_file(skill_name, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

    # Determine content type based on extension
    content_type = "text/plain; charset=utf-8"
    if file_path.endswith(".json"):
        content_type = "application/json"
    elif file_path.endswith(".md"):
        content_type = "text/markdown; charset=utf-8"
    elif file_path.endswith(".py"):
        content_type = "text/x-python"
    elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        content_type = "text/yaml"

    response.headers["Content-Type"] = content_type
    response.headers["Cache-Control"] = "public, max-age=300"

    return content


@app.head(
    "/.well-known/skills/index.json",
    tags=["RFC Well-Known"],
    summary="HEAD request for index.json"
)
async def head_skills_index(response: Response):
    """RFC requires support for HEAD requests."""
    response.headers["Content-Type"] = "application/json"
    response.headers["Cache-Control"] = "public, max-age=300"
    return Response(status_code=200)


@app.head(
    "/.well-known/skills/{skill_name}/SKILL.md",
    tags=["RFC Well-Known"],
    summary="HEAD request for SKILL.md"
)
async def head_skill_md(skill_name: str, response: Response):
    """RFC requires support for HEAD requests."""
    skill = services.registry.get_skill_by_slug(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=300"
    return Response(status_code=200)


# =============================================================================
# Progressive Disclosure Endpoints
# =============================================================================

@app.get(
    "/api/v1/skills/level1",
    response_model=List[SkillLevel1],
    tags=["Progressive Disclosure"],
    summary="Get all skills at Level 1 (minimal metadata)"
)
async def get_skills_level1():
    """
    Returns minimal metadata for all skills (~100 tokens per skill).
    Use this for initial discovery and filtering.
    """
    skills = services.registry.list_skills()
    return [services.renderer.get_skill_level1(s) for s in skills]


@app.get(
    "/api/v1/skills/{skill_name}/level2",
    response_model=SkillLevel2,
    tags=["Progressive Disclosure"],
    summary="Get skill at Level 2 (full SKILL.md content)"
)
async def get_skill_level2(skill_name: str):
    """
    Returns full SKILL.md content for a skill (~5k tokens max).
    Use this when a skill is activated/selected.
    """
    skill = services.registry.get_skill_by_slug(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    return services.renderer.get_skill_level2(skill)


@app.get(
    "/api/v1/skills/{skill_name}/level3",
    response_model=SkillLevel3,
    tags=["Progressive Disclosure"],
    summary="Get skill at Level 3 (with all resources)"
)
async def get_skill_level3(skill_name: str):
    """
    Returns full skill with all supporting resources.
    Use this during task execution when resources are needed.
    """
    skill = services.registry.get_skill_by_slug(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    # Get all available resources
    files = services.renderer.list_skill_files(skill_name)
    resources = {}
    for file_path in files:
        content = services.renderer.read_skill_file(skill_name, file_path)
        if content:
            resources[file_path] = content

    return services.renderer.get_skill_level3(skill, resources)


# =============================================================================
# Core API Endpoints
# =============================================================================

@app.post(
    "/skills",
    response_model=RegisterResponse,
    tags=["Skills Management"],
    summary="Register a new skill"
)
async def register_skill(skill_input: SkillInput):
    """
    Register a new skill in the registry.
    Automatically generates SKILL.md and updates the index.
    """
    # Create full skill object
    skill = Skill(**skill_input.model_dump())

    # 1. Save to Registry (JSON)
    saved_skill = services.registry.register_skill(skill)

    # 2. Index in Vector Store
    services.vector_store.add_skill(saved_skill)

    # 3. Generate and save SKILL.md
    services.renderer.save_skill_md(saved_skill)

    # 4. Update index.json
    all_skills = services.registry.list_skills()
    services.renderer.save_index_json(all_skills)

    return RegisterResponse(
        id=saved_skill.id,
        slug=saved_skill.slug,
        message="Skill registered and indexed successfully"
    )


@app.get(
    "/skills",
    response_model=List[Skill],
    tags=["Skills Management"],
    summary="List all registered skills"
)
async def list_skills():
    """Returns all registered skills."""
    return services.registry.list_skills()


@app.get(
    "/skills/{skill_id}",
    response_model=Skill,
    tags=["Skills Management"],
    summary="Get a skill by ID"
)
async def get_skill(skill_id: str):
    """Returns a specific skill by its ID."""
    skill = services.registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill with ID '{skill_id}' not found")
    return skill


@app.delete(
    "/skills/{skill_id}",
    tags=["Skills Management"],
    summary="Delete a skill"
)
async def delete_skill(skill_id: str):
    """Delete a skill from the registry."""
    deleted = services.registry.delete_skill(skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Skill with ID '{skill_id}' not found")

    # Update index.json
    all_skills = services.registry.list_skills()
    services.renderer.save_index_json(all_skills)

    return {"message": "Skill deleted successfully"}


@app.get(
    "/search",
    response_model=List[SearchResult],
    tags=["Search"],
    summary="Semantic search for skills"
)
async def search_skills(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=100, description="Maximum results to return")
):
    """
    Perform semantic search across registered skills.
    Uses vector embeddings for similarity matching.
    """
    results = services.vector_store.search_ids(q, limit=limit)

    search_results = []
    for skill_id, distance in results:
        skill = services.registry.get_skill(skill_id)
        if skill:
            # Convert distance to similarity score
            score = 1 / (1 + distance)
            search_results.append(SearchResult(skill=skill, score=score))

    return search_results


# =============================================================================
# Discovery Client Endpoints
# =============================================================================

@app.get(
    "/api/v1/discover/{origin:path}",
    response_model=DiscoveryResult,
    tags=["Discovery"],
    summary="Discover skills from a remote server"
)
async def discover_skills(origin: str):
    """
    Discover skills from a remote server implementing the RFC protocol.
    Fetches the index.json from the origin's /.well-known/skills/ endpoint.
    """
    try:
        result = await services.discovery.discover_from_origin(origin)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to discover skills from '{origin}': {str(e)}"
        )


@app.get(
    "/api/v1/discover/{origin:path}/{skill_name}/level2",
    response_model=SkillLevel2,
    tags=["Discovery"],
    summary="Fetch Level 2 skill from remote server"
)
async def fetch_remote_skill_level2(origin: str, skill_name: str):
    """
    Fetch the full SKILL.md content from a remote server.
    """
    try:
        skill = await services.discovery.client.get_skill_level2(origin, skill_name)
        return skill
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch skill '{skill_name}' from '{origin}': {str(e)}"
        )


@app.post(
    "/api/v1/trusted-origins",
    tags=["Discovery"],
    summary="Add a trusted origin"
)
async def add_trusted_origin(origin: str):
    """Add an origin to the trusted list for discovery."""
    services.discovery.add_trusted_origin(origin)
    return {"message": f"Added '{origin}' to trusted origins"}


@app.get(
    "/api/v1/trusted-origins",
    response_model=List[str],
    tags=["Discovery"],
    summary="List trusted origins"
)
async def list_trusted_origins():
    """List all trusted origins."""
    return services.discovery._trusted_origins


@app.delete(
    "/api/v1/trusted-origins",
    tags=["Discovery"],
    summary="Remove a trusted origin"
)
async def remove_trusted_origin(origin: str):
    """Remove an origin from the trusted list."""
    services.discovery.remove_trusted_origin(origin)
    return {"message": f"Removed '{origin}' from trusted origins"}


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "rfc_version": "0.1"
    }
