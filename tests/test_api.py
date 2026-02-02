"""
Integration tests for Agent Skills Registry API.
Tests RFC Well-Known endpoints and progressive disclosure.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestSkillManagement:
    """Tests for core skill management endpoints."""

    def test_register_skill(self):
        """Test registering a new skill."""
        skill_data = {
            "name": "Test Skill",
            "description": "A test skill for unit testing purposes.",
            "tags": ["test", "unit-test"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Test input"}
                },
                "required": ["input"]
            },
            "version": "1.0.0",
            "author": "Test Author"
        }

        response = client.post("/skills", json=skill_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "slug" in data
        assert data["slug"] == "test-skill"
        assert data["message"] == "Skill registered and indexed successfully"

    def test_list_skills(self):
        """Test listing all skills."""
        response = client.get("/skills")
        assert response.status_code == 200
        skills = response.json()
        assert isinstance(skills, list)

    def test_search_skills(self):
        """Test semantic search for skills."""
        # First register a skill
        skill_data = {
            "name": "Python Data Analysis",
            "description": "Analyze data using Pandas and NumPy in Python.",
            "tags": ["python", "pandas", "data-science"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data to analyze"}
                }
            }
        }
        client.post("/skills", json=skill_data)

        # Search for the skill
        response = client.get("/search?q=data analysis python")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)


class TestRFCWellKnown:
    """Tests for RFC Well-Known endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Register a test skill before each test."""
        skill_data = {
            "name": "Web Search",
            "description": "Search the web for information on any topic.",
            "tags": ["search", "web", "information"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            "version": "1.0.0",
            "author": "Test"
        }
        client.post("/skills", json=skill_data)

    def test_get_index_json(self):
        """Test RFC index.json endpoint."""
        response = client.get("/.well-known/skills/index.json")
        assert response.status_code == 200

        # Check content type header
        assert "application/json" in response.headers.get("content-type", "")

        # Check cache control
        assert "Cache-Control" in response.headers

        data = response.json()
        assert "version" in data
        assert "skills" in data
        assert isinstance(data["skills"], list)

        # Each skill should have name, description, files
        if data["skills"]:
            skill = data["skills"][0]
            assert "name" in skill
            assert "description" in skill
            assert "files" in skill

    def test_get_skill_md(self):
        """Test RFC SKILL.md endpoint."""
        response = client.get("/.well-known/skills/web-search/SKILL.md")
        assert response.status_code == 200

        # Check content type
        assert "text/markdown" in response.headers.get("content-type", "")

        # Check content structure (YAML frontmatter + Markdown)
        content = response.text
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content

    def test_skill_md_not_found(self):
        """Test 404 for non-existent skill."""
        response = client.get("/.well-known/skills/nonexistent-skill/SKILL.md")
        assert response.status_code == 404

    def test_head_index_json(self):
        """Test HEAD request for index.json."""
        response = client.head("/.well-known/skills/index.json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_head_skill_md(self):
        """Test HEAD request for SKILL.md."""
        response = client.head("/.well-known/skills/web-search/SKILL.md")
        assert response.status_code == 200


class TestProgressiveDisclosure:
    """Tests for Progressive Disclosure endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Register a test skill before each test."""
        skill_data = {
            "name": "Calculator",
            "description": "Evaluate mathematical expressions.",
            "tags": ["math", "utility"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                }
            },
            "documentation": "Extended documentation for the calculator skill.",
            "examples": [
                {
                    "description": "Simple addition",
                    "input": {"expression": "2 + 2"},
                    "output": {"result": 4}
                }
            ],
            "version": "2.0.0",
            "author": "Math Team"
        }
        client.post("/skills", json=skill_data)

    def test_level1_all_skills(self):
        """Test Level 1 endpoint - minimal metadata."""
        response = client.get("/api/v1/skills/level1")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        if data:
            skill = data[0]
            # Level 1 should only have name and description
            assert "name" in skill
            assert "description" in skill
            # Should NOT have full details
            assert "input_schema" not in skill
            assert "documentation" not in skill

    def test_level2_skill(self):
        """Test Level 2 endpoint - full SKILL.md content."""
        response = client.get("/api/v1/skills/calculator/level2")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "calculator"
        assert "description" in data
        assert "version" in data
        assert "input_schema" in data
        assert "tags" in data

    def test_level3_skill(self):
        """Test Level 3 endpoint - with resources."""
        response = client.get("/api/v1/skills/calculator/level3")
        assert response.status_code == 200

        data = response.json()
        assert "skill" in data
        assert "resources" in data
        assert isinstance(data["resources"], dict)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "rfc_version" in data


class TestSkillSlugGeneration:
    """Tests for RFC-compliant slug generation."""

    def test_slug_from_name_with_spaces(self):
        """Test slug generation from name with spaces."""
        skill_data = {
            "name": "My Great Skill",
            "description": "A skill with spaces in the name.",
            "input_schema": {"type": "object"}
        }
        response = client.post("/skills", json=skill_data)
        assert response.status_code == 200
        assert response.json()["slug"] == "my-great-skill"

    def test_slug_from_name_with_special_chars(self):
        """Test slug generation removes special characters."""
        skill_data = {
            "name": "Test@Skill#123",
            "description": "A skill with special characters.",
            "input_schema": {"type": "object"}
        }
        response = client.post("/skills", json=skill_data)
        assert response.status_code == 200
        # Special chars removed, hyphens used for separation
        slug = response.json()["slug"]
        assert "@" not in slug
        assert "#" not in slug


class TestTrustedOrigins:
    """Tests for trusted origins management."""

    def test_add_trusted_origin(self):
        """Test adding a trusted origin."""
        response = client.post("/api/v1/trusted-origins?origin=https://example.com")
        assert response.status_code == 200

    def test_list_trusted_origins(self):
        """Test listing trusted origins."""
        # Add an origin first
        client.post("/api/v1/trusted-origins?origin=https://test.com")

        response = client.get("/api/v1/trusted-origins")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_remove_trusted_origin(self):
        """Test removing a trusted origin."""
        # Add first
        client.post("/api/v1/trusted-origins?origin=https://remove.com")

        # Remove
        response = client.delete("/api/v1/trusted-origins?origin=https://remove.com")
        assert response.status_code == 200
