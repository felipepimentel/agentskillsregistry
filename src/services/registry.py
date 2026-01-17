import json
import os
from typing import List, Optional
from src.schemas.models import Skill

class RegistryService:
    def __init__(self, storage_path: str = "data/skills.json"):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                json.dump([], f)

    def _load(self) -> List[dict]:
        with open(self.storage_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save(self, skills: List[dict]):
        with open(self.storage_path, "w") as f:
            json.dump(skills, f, indent=2)

    def list_skills(self) -> List[Skill]:
        data = self._load()
        return [Skill(**item) for item in data]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        skills = self.list_skills()
        for s in skills:
            if s.id == skill_id:
                return s
        return None

    def register_skill(self, skill: Skill) -> Skill:
        skills = self._load()
        # Check for duplicates by name? For now allow, just append or update?
        # Let's simple append
        skills.append(skill.dict())
        self._save(skills)
        return skill
