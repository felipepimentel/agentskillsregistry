"""
Registry service for persistent skill storage.
Manages skills in JSON format and generates RFC-compliant files.
"""
import json
import os
from typing import List, Optional
from src.schemas.models import Skill, SkillFile, normalize_skill_name


class RegistryService:
    """Service for managing skill persistence."""

    def __init__(self, storage_path: str = "data/skills.json"):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage directory and file exist."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                json.dump([], f)

    def _load(self) -> List[dict]:
        """Load skills from JSON storage."""
        with open(self.storage_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save(self, skills: List[dict]):
        """Save skills to JSON storage."""
        with open(self.storage_path, "w") as f:
            json.dump(skills, f, indent=2)

    def _ensure_skill_fields(self, skill_data: dict) -> dict:
        """Ensure all required fields exist in skill data (migration support)."""
        # Add slug if missing
        if "slug" not in skill_data or not skill_data["slug"]:
            skill_data["slug"] = normalize_skill_name(skill_data.get("name", ""))

        # Add files if missing
        if "files" not in skill_data:
            skill_data["files"] = [{"path": "SKILL.md", "content_type": "text/markdown"}]

        # Add version if missing
        if "version" not in skill_data:
            skill_data["version"] = "1.0.0"

        # Add optional fields with defaults
        if "output_schema" not in skill_data:
            skill_data["output_schema"] = None
        if "author" not in skill_data:
            skill_data["author"] = None
        if "documentation" not in skill_data:
            skill_data["documentation"] = None
        if "examples" not in skill_data:
            skill_data["examples"] = None
        if "updated_at" not in skill_data:
            skill_data["updated_at"] = skill_data.get("created_at", "")

        return skill_data

    def list_skills(self) -> List[Skill]:
        """List all registered skills."""
        data = self._load()
        skills = []
        for item in data:
            item = self._ensure_skill_fields(item)
            skills.append(Skill(**item))
        return skills

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by its ID."""
        skills = self.list_skills()
        for s in skills:
            if s.id == skill_id:
                return s
        return None

    def get_skill_by_slug(self, slug: str) -> Optional[Skill]:
        """Get a skill by its RFC-compliant slug."""
        skills = self.list_skills()
        for s in skills:
            if s.slug == slug:
                return s
        return None

    def register_skill(self, skill: Skill) -> Skill:
        """
        Register a new skill.
        Updates if a skill with the same slug already exists.
        """
        skills_data = self._load()

        # Check for existing skill with same slug
        existing_index = None
        for i, item in enumerate(skills_data):
            item = self._ensure_skill_fields(item)
            if item.get("slug") == skill.slug:
                existing_index = i
                break

        skill_dict = skill.model_dump()

        if existing_index is not None:
            # Update existing skill, preserve original ID and created_at
            skill_dict["id"] = skills_data[existing_index].get("id", skill.id)
            skill_dict["created_at"] = skills_data[existing_index].get("created_at", skill.created_at)
            skills_data[existing_index] = skill_dict
        else:
            skills_data.append(skill_dict)

        self._save(skills_data)
        return Skill(**skill_dict)

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill by ID. Returns True if deleted, False if not found."""
        skills_data = self._load()
        initial_length = len(skills_data)

        skills_data = [s for s in skills_data if s.get("id") != skill_id]

        if len(skills_data) < initial_length:
            self._save(skills_data)
            return True
        return False

    def delete_skill_by_slug(self, slug: str) -> bool:
        """Delete a skill by slug. Returns True if deleted, False if not found."""
        skills_data = self._load()
        initial_length = len(skills_data)

        skills_data = [
            s for s in skills_data
            if self._ensure_skill_fields(s).get("slug") != slug
        ]

        if len(skills_data) < initial_length:
            self._save(skills_data)
            return True
        return False

    def add_skill_file(self, skill_id: str, file: SkillFile) -> Optional[Skill]:
        """Add a file reference to a skill."""
        skills_data = self._load()

        for i, item in enumerate(skills_data):
            if item.get("id") == skill_id:
                if "files" not in item:
                    item["files"] = []
                # Check if file already exists
                existing_paths = [f.get("path") for f in item["files"]]
                if file.path not in existing_paths:
                    item["files"].append(file.model_dump())
                skills_data[i] = item
                self._save(skills_data)
                return Skill(**self._ensure_skill_fields(item))

        return None

    def search_by_tags(self, tags: List[str]) -> List[Skill]:
        """Search skills that have any of the specified tags."""
        skills = self.list_skills()
        return [s for s in skills if any(tag in s.tags for tag in tags)]
