"""
Discovery service for fetching skills from remote servers.
Implements RFC client-side discovery protocol.
"""
import json
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import httpx
from src.schemas.models import (
    RemoteSkillInfo, DiscoveryResult, SkillIndex,
    SkillLevel1, SkillLevel2, SkillLevel3
)


class DiscoveryClient:
    """
    Client for discovering skills from remote servers following RFC protocol.

    Implements the progressive disclosure model:
    - Level 1: Index metadata only (~100 tokens)
    - Level 2: Full SKILL.md (~5k tokens max)
    - Level 3: Supporting resources (on-demand)
    """

    WELL_KNOWN_PATH = "/.well-known/skills/"
    INDEX_FILE = "index.json"
    SKILL_FILE = "SKILL.md"

    def __init__(
        self,
        timeout: float = 30.0,
        cache_ttl: int = 900,  # 15 minutes
        user_agent: str = "AgentSkillsRegistry/1.0"
    ):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.user_agent = user_agent
        self._cache: Dict[str, Any] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/markdown, text/plain"
        }

    async def discover(self, origin: str) -> DiscoveryResult:
        """
        Discover all skills from a remote server (Level 1).

        Args:
            origin: Base URL of the server (e.g., "https://example.com")

        Returns:
            DiscoveryResult with list of available skills
        """
        # Normalize origin URL
        if not origin.startswith(("http://", "https://")):
            origin = f"https://{origin}"
        origin = origin.rstrip("/")

        index_url = f"{origin}{self.WELL_KNOWN_PATH}{self.INDEX_FILE}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(index_url, headers=self._get_headers())
            response.raise_for_status()

            index_data = response.json()
            skills_info = []

            for skill_entry in index_data.get("skills", []):
                skill_url = f"{origin}{self.WELL_KNOWN_PATH}{skill_entry['name']}/"
                skills_info.append(RemoteSkillInfo(
                    origin=origin,
                    name=skill_entry["name"],
                    description=skill_entry.get("description", ""),
                    files=skill_entry.get("files", ["SKILL.md"]),
                    skill_url=skill_url
                ))

            return DiscoveryResult(
                origin=origin,
                skills=skills_info
            )

    async def fetch_skill_md(self, origin: str, skill_name: str) -> str:
        """
        Fetch the SKILL.md content for a specific skill (Level 2).

        Args:
            origin: Base URL of the server
            skill_name: RFC-compliant skill name/slug

        Returns:
            SKILL.md content as string
        """
        if not origin.startswith(("http://", "https://")):
            origin = f"https://{origin}"
        origin = origin.rstrip("/")

        skill_url = f"{origin}{self.WELL_KNOWN_PATH}{skill_name}/{self.SKILL_FILE}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(skill_url, headers=self._get_headers())
            response.raise_for_status()
            return response.text

    async def fetch_skill_resource(
        self,
        origin: str,
        skill_name: str,
        resource_path: str
    ) -> str:
        """
        Fetch an additional resource file for a skill (Level 3).

        Args:
            origin: Base URL of the server
            skill_name: RFC-compliant skill name/slug
            resource_path: Relative path to the resource

        Returns:
            Resource content as string
        """
        if not origin.startswith(("http://", "https://")):
            origin = f"https://{origin}"
        origin = origin.rstrip("/")

        resource_url = f"{origin}{self.WELL_KNOWN_PATH}{skill_name}/{resource_path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(resource_url, headers=self._get_headers())
            response.raise_for_status()
            return response.text

    async def fetch_all_resources(
        self,
        origin: str,
        skill_name: str,
        files: List[str]
    ) -> Dict[str, str]:
        """
        Fetch all resources for a skill in parallel.

        Args:
            origin: Base URL of the server
            skill_name: RFC-compliant skill name/slug
            files: List of file paths to fetch

        Returns:
            Dict mapping file paths to content
        """
        async def fetch_one(file_path: str) -> tuple:
            try:
                content = await self.fetch_skill_resource(origin, skill_name, file_path)
                return (file_path, content)
            except Exception:
                return (file_path, None)

        tasks = [fetch_one(f) for f in files]
        results = await asyncio.gather(*tasks)

        return {path: content for path, content in results if content is not None}

    def parse_skill_md(self, content: str) -> Dict[str, Any]:
        """
        Parse SKILL.md content into structured data.
        Extracts YAML frontmatter and Markdown body.

        Args:
            content: SKILL.md file content

        Returns:
            Dict with 'metadata' and 'body' keys
        """
        result = {"metadata": {}, "body": ""}

        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            result["body"] = content
            return result

        # Find closing frontmatter delimiter
        end_index = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end_index = i
                break

        if end_index is None:
            result["body"] = content
            return result

        # Parse YAML frontmatter (simple key-value parsing)
        frontmatter_lines = lines[1:end_index]
        current_key = None
        current_list = None

        for line in frontmatter_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for list item
            if stripped.startswith("- "):
                if current_list is not None:
                    current_list.append(stripped[2:].strip())
                continue

            # Check for key-value
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                if value:
                    # Simple key-value
                    result["metadata"][key] = value.strip('"\'')
                    current_key = None
                    current_list = None
                else:
                    # Start of list or nested object
                    current_key = key
                    current_list = []
                    result["metadata"][key] = current_list

        result["body"] = "\n".join(lines[end_index + 1:]).strip()
        return result

    async def get_skill_level1(self, origin: str) -> List[SkillLevel1]:
        """
        Get Level 1 (minimal) representation of all skills from a server.

        Args:
            origin: Base URL of the server

        Returns:
            List of SkillLevel1 objects
        """
        discovery = await self.discover(origin)
        return [
            SkillLevel1(name=s.name, description=s.description)
            for s in discovery.skills
        ]

    async def get_skill_level2(self, origin: str, skill_name: str) -> SkillLevel2:
        """
        Get Level 2 (full SKILL.md) representation of a skill.

        Args:
            origin: Base URL of the server
            skill_name: RFC-compliant skill name/slug

        Returns:
            SkillLevel2 object
        """
        content = await self.fetch_skill_md(origin, skill_name)
        parsed = self.parse_skill_md(content)
        metadata = parsed["metadata"]

        return SkillLevel2(
            name=metadata.get("name", skill_name),
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0.0"),
            author=metadata.get("author"),
            tags=metadata.get("tags", []) if isinstance(metadata.get("tags"), list) else [],
            input_schema=metadata.get("input_schema", {}),
            output_schema=metadata.get("output_schema"),
            documentation=parsed["body"] or None,
            examples=None  # Would need more complex parsing
        )

    async def get_skill_level3(
        self,
        origin: str,
        skill_name: str,
        files: Optional[List[str]] = None
    ) -> SkillLevel3:
        """
        Get Level 3 (full with resources) representation of a skill.

        Args:
            origin: Base URL of the server
            skill_name: RFC-compliant skill name/slug
            files: List of files to fetch (if None, fetches all from discovery)

        Returns:
            SkillLevel3 object
        """
        # Get Level 2 first
        skill = await self.get_skill_level2(origin, skill_name)

        # Determine files to fetch
        if files is None:
            discovery = await self.discover(origin)
            for s in discovery.skills:
                if s.name == skill_name:
                    files = s.files
                    break
            files = files or ["SKILL.md"]

        # Fetch all resources
        resources = await self.fetch_all_resources(origin, skill_name, files)

        return SkillLevel3(skill=skill, resources=resources)

    async def check_origin(self, origin: str) -> bool:
        """
        Check if an origin supports the RFC skills discovery protocol.

        Args:
            origin: Base URL to check

        Returns:
            True if the origin has a valid /.well-known/skills/index.json
        """
        try:
            await self.discover(origin)
            return True
        except Exception:
            return False


class DiscoveryService:
    """
    Service for managing skill discovery from multiple origins.
    Provides caching and aggregation of discovered skills.
    """

    def __init__(self):
        self.client = DiscoveryClient()
        self._discovered_skills: Dict[str, DiscoveryResult] = {}
        self._trusted_origins: List[str] = []

    def add_trusted_origin(self, origin: str):
        """Add an origin to the trusted list."""
        if origin not in self._trusted_origins:
            self._trusted_origins.append(origin)

    def remove_trusted_origin(self, origin: str):
        """Remove an origin from the trusted list."""
        if origin in self._trusted_origins:
            self._trusted_origins.remove(origin)

    def is_trusted(self, origin: str) -> bool:
        """Check if an origin is trusted."""
        return origin in self._trusted_origins

    async def discover_from_origin(self, origin: str) -> DiscoveryResult:
        """
        Discover skills from a specific origin.
        Caches the result.
        """
        result = await self.client.discover(origin)
        self._discovered_skills[origin] = result
        return result

    async def discover_from_all_trusted(self) -> List[DiscoveryResult]:
        """Discover skills from all trusted origins in parallel."""
        tasks = [self.discover_from_origin(o) for o in self._trusted_origins]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        return [r for r in results if isinstance(r, DiscoveryResult)]

    def get_cached_skills(self, origin: Optional[str] = None) -> List[RemoteSkillInfo]:
        """
        Get cached skills, optionally filtered by origin.
        """
        if origin:
            result = self._discovered_skills.get(origin)
            return result.skills if result else []

        all_skills = []
        for result in self._discovered_skills.values():
            all_skills.extend(result.skills)
        return all_skills

    async def search_discovered(self, query: str, limit: int = 10) -> List[RemoteSkillInfo]:
        """
        Simple text search across discovered skills.
        For more advanced search, use the vector store.
        """
        query_lower = query.lower()
        results = []

        for skill in self.get_cached_skills():
            score = 0
            if query_lower in skill.name.lower():
                score += 2
            if query_lower in skill.description.lower():
                score += 1

            if score > 0:
                results.append((skill, score))

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in results[:limit]]
