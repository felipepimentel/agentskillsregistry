import urllib.request
import json
import time

API_URL = "http://localhost:8000"

SAMPLE_SKILLS = [
    {
        "name": "web_search",
        "description": "Searches the public web for information on a given topic. Useful for retrieving up-to-date news, facts, or documentation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        },
        "tags": ["search", "internet", "information"]
    },
    {
        "name": "file_reader",
        "description": "Reads the content of a file from the local filesystem. Supports text and markdown files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"}
            },
            "required": ["path"]
        },
        "tags": ["filesystem", "io", "read"]
    },
    {
        "name": "image_generator",
        "description": "Generates an image based on a text prompt using a diffusion model. Returns a URL or base64 string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description"}
            },
            "required": ["prompt"]
        },
        "tags": ["ai", "image", "creative"]
    },
    {
        "name": "calculator",
        "description": "Evaluates mathematical expressions. Can handle basic arithmetic, trigonometry, and logarithms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"]
        },
        "tags": ["math", "utility", "computation"]
    }
]

def register_skills():
    print(f"Connecting to {API_URL}...")
    for skill in SAMPLE_SKILLS:
        req = urllib.request.Request(
            f"{API_URL}/skills",
            data=json.dumps(skill).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                print(f"Registered {skill['name']}: {result['message']}")
        except urllib.error.URLError as e:
            print(f"Failed to register {skill['name']}: {e}")

def convert_results_to_serializable(results):
    serializable_results = []
    for res in results:
        serializable_results.append({
            "skill": res.get("skill"),
            "score": res.get("score")
        })
    return serializable_results

def test_search():
    queries = [
        "How do I find the capital of France?",
        "I need to read a config file",
        "Calculate 2 + 2",
        "Draw a cat"
    ]
    
    print("\nTesting Semantic Search:")
    for q in queries:
        encoded_q = urllib.parse.quote(q)
        try:
            with urllib.request.urlopen(f"{API_URL}/search?q={encoded_q}&limit=2") as response:
                results = json.loads(response.read().decode())
                print(f"\nQuery: '{q}'")
                for res in results:
                    name = res['skill']['name']
                    score = res['score']
                    desc = res['skill']['description']
                    print(f"  - {name} (Score: {score:.4f})")
        except Exception as e:
            print(f"Search failed: {e}")

if __name__ == "__main__":
    # Wait a bit for server to be ready if running in CI/Script
    # time.sleep(2)
    register_skills()
    test_search()
