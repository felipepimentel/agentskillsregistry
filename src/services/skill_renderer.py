"""
Service for rendering skills to RFC-compliant formats.
Generates SKILL.md files and index.json structures.
"""
import json
import os
from typing import Dict, Any, List, Optional
from src.schemas.models import (
    Skill, SkillIndex, SkillIndexEntry, SkillMetadata,
    SkillLevel1, SkillLevel2, SkillLevel3
)


class SkillRenderer:
    """Renders skills to various RFC-compliant formats."""

    def __init__(self, skills_dir: str = "data/well-known/skills"):
        self.skills_dir = skills_dir
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the skills directory exists."""
        os.makedirs(self.skills_dir, exist_ok=True)

    def render_skill_md(self, skill: Skill) -> str:
        """
        Render a skill to SKILL.md format with YAML frontmatter.

        Format per RFC:
        ---
        name: skill-name
        description: Brief description
        version: 1.0.0
        ...
        ---

        # Skill Name

        Extended documentation...
        """
        # Build YAML frontmatter
        frontmatter_data = {
            "name": skill.slug,
            "description": skill.description,
            "version": skill.version,
        }

        if skill.author:
            frontmatter_data["author"] = skill.author

        if skill.tags:
            frontmatter_data["tags"] = skill.tags

        if skill.input_schema:
            frontmatter_data["input_schema"] = skill.input_schema

        if skill.output_schema:
            frontmatter_data["output_schema"] = skill.output_schema

        # Build YAML manually for cleaner output
        yaml_lines = ["---"]
        yaml_lines.append(f"name: {frontmatter_data['name']}")
        yaml_lines.append(f"description: \"{frontmatter_data['description']}\"")
        yaml_lines.append(f"version: {frontmatter_data['version']}")

        if skill.author:
            yaml_lines.append(f"author: {skill.author}")

        if skill.tags:
            yaml_lines.append("tags:")
            for tag in skill.tags:
                yaml_lines.append(f"  - {tag}")

        if skill.input_schema:
            yaml_lines.append("input_schema:")
            yaml_lines.extend(self._dict_to_yaml(skill.input_schema, indent=2))

        if skill.output_schema:
            yaml_lines.append("output_schema:")
            yaml_lines.extend(self._dict_to_yaml(skill.output_schema, indent=2))

        yaml_lines.append("---")
        yaml_lines.append("")

        # Build Markdown content
        md_lines = []
        md_lines.append(f"# {skill.name}")
        md_lines.append("")
        md_lines.append(skill.description)
        md_lines.append("")

        # Add documentation if present
        if skill.documentation:
            md_lines.append("## Documentation")
            md_lines.append("")
            md_lines.append(skill.documentation)
            md_lines.append("")

        # Add input schema section
        md_lines.append("## Input Schema")
        md_lines.append("")
        md_lines.append("```json")
        md_lines.append(json.dumps(skill.input_schema, indent=2))
        md_lines.append("```")
        md_lines.append("")

        # Add output schema if present
        if skill.output_schema:
            md_lines.append("## Output Schema")
            md_lines.append("")
            md_lines.append("```json")
            md_lines.append(json.dumps(skill.output_schema, indent=2))
            md_lines.append("```")
            md_lines.append("")

        # Add examples if present
        if skill.examples:
            md_lines.append("## Examples")
            md_lines.append("")
            for i, example in enumerate(skill.examples, 1):
                md_lines.append(f"### Example {i}")
                md_lines.append("")
                if "description" in example:
                    md_lines.append(example["description"])
                    md_lines.append("")
                if "input" in example:
                    md_lines.append("**Input:**")
                    md_lines.append("```json")
                    md_lines.append(json.dumps(example["input"], indent=2))
                    md_lines.append("```")
                    md_lines.append("")
                if "output" in example:
                    md_lines.append("**Output:**")
                    md_lines.append("```json")
                    md_lines.append(json.dumps(example["output"], indent=2))
                    md_lines.append("```")
                    md_lines.append("")

        # Add tags section
        if skill.tags:
            md_lines.append("## Tags")
            md_lines.append("")
            md_lines.append(", ".join(f"`{tag}`" for tag in skill.tags))
            md_lines.append("")

        return "\n".join(yaml_lines + md_lines)

    def _dict_to_yaml(self, d: Dict[str, Any], indent: int = 0) -> List[str]:
        """Convert a dict to YAML-like lines with proper indentation."""
        lines = []
        prefix = " " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(self._dict_to_yaml(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.extend(self._dict_to_yaml(item, indent + 4))
                    else:
                        lines.append(f"{prefix}  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{prefix}{key}: {str(value).lower()}")
            elif isinstance(value, str):
                # Quote strings with special characters
                if any(c in value for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`']):
                    lines.append(f'{prefix}{key}: "{value}"')
                else:
                    lines.append(f"{prefix}{key}: {value}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return lines

    def save_skill_md(self, skill: Skill) -> str:
        """
        Save a skill's SKILL.md file to the well-known directory.
        Returns the path to the saved file.
        """
        skill_dir = os.path.join(self.skills_dir, skill.slug)
        os.makedirs(skill_dir, exist_ok=True)

        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        content = self.render_skill_md(skill)

        with open(skill_md_path, "w") as f:
            f.write(content)

        return skill_md_path

    def render_index_json(self, skills: List[Skill]) -> SkillIndex:
        """
        Render the RFC-compliant index.json for all skills.
        """
        entries = []
        for skill in skills:
            # Build files list from skill's files
            files = [f.path for f in skill.files]

            entry = SkillIndexEntry(
                name=skill.slug,
                description=skill.description[:1024],  # Enforce max length
                files=files
            )
            entries.append(entry)

        return SkillIndex(version="0.1", skills=entries)

    def save_index_json(self, skills: List[Skill]) -> str:
        """
        Save the index.json file to the well-known directory.
        Returns the path to the saved file.
        """
        index = self.render_index_json(skills)
        index_path = os.path.join(self.skills_dir, "index.json")

        with open(index_path, "w") as f:
            json.dump(index.model_dump(), f, indent=2)

        return index_path

    def get_skill_level1(self, skill: Skill) -> SkillLevel1:
        """Get Level 1 (minimal) representation of a skill."""
        return SkillLevel1(
            name=skill.slug,
            description=skill.description
        )

    def get_skill_level2(self, skill: Skill) -> SkillLevel2:
        """Get Level 2 (SKILL.md content) representation of a skill."""
        return SkillLevel2(
            name=skill.slug,
            description=skill.description,
            version=skill.version,
            author=skill.author,
            tags=skill.tags,
            input_schema=skill.input_schema,
            output_schema=skill.output_schema,
            documentation=skill.documentation,
            examples=skill.examples
        )

    def get_skill_level3(self, skill: Skill, resources: Optional[Dict[str, str]] = None) -> SkillLevel3:
        """Get Level 3 (full with resources) representation of a skill."""
        level2 = self.get_skill_level2(skill)
        return SkillLevel3(
            skill=level2,
            resources=resources or {}
        )

    def read_skill_file(self, skill_slug: str, file_path: str) -> Optional[str]:
        """
        Read a file from a skill's directory.
        Returns the file content or None if not found.
        """
        full_path = os.path.join(self.skills_dir, skill_slug, file_path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                return f.read()
        return None

    def list_skill_files(self, skill_slug: str) -> List[str]:
        """List all files in a skill's directory."""
        skill_dir = os.path.join(self.skills_dir, skill_slug)
        if not os.path.exists(skill_dir):
            return []

        files = []
        for root, _, filenames in os.walk(skill_dir):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), skill_dir)
                files.append(rel_path)
        return files

    def save_skill_resource(self, skill_slug: str, file_path: str, content: str) -> str:
        """
        Save an additional resource file for a skill.
        Returns the full path to the saved file.
        """
        skill_dir = os.path.join(self.skills_dir, skill_slug)
        full_path = os.path.join(skill_dir, file_path)

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w") as f:
            f.write(content)

        return full_path
