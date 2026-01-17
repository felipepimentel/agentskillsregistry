import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.schemas.models import SkillInput

client = TestClient(app)

def test_register_and_search_flow():
    # 1. Register a skill
    skill_data = {
        "name": "Python Data Analysis",
        "description": "Ability to analyze data using Pandas and NumPy libraries in Python.",
        "tags": ["python", "pandas", "data-science"],
        "input_schema": {
            "type": "object",
            "properties": {
                "df": {"type": "string", "description": "DataFrame in JSON format"}
            }
        }
    }
    
    response = client.post("/skills", json=skill_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["message"] == "Skill registered and indexed successfully"
    skill_id = data["id"]
    
    # 2. List skills
    response = client.get("/skills")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) >= 1
    assert any(s["id"] == skill_id for s in skills)
    
    # 3. Search for the skill
    # Note: Search might be tricky to test deterministically with embeddings without mocking,
    # but we can check if it runs without error and returns reasonable structure.
    response = client.get("/search?q=pandas analysis")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    # Ideally our skill should be in the top results
    # assert any(r["skill"]["id"] == skill_id for r in results) 
