#!/usr/bin/env python3
"""
Seed script for Agent Skills Registry.
Registers RFC-compliant sample skills and tests the API.
"""
import urllib.request
import urllib.parse
import json
import time

API_URL = "http://localhost:8000"

# RFC-compliant sample skills with full metadata
SAMPLE_SKILLS = [
    {
        "name": "Web Search",
        "description": "Searches the public web for information on a given topic. Useful for retrieving up-to-date news, facts, documentation, or any publicly available information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"}
                        }
                    }
                }
            }
        },
        "tags": ["search", "internet", "information", "web"],
        "version": "1.0.0",
        "author": "Skills Registry",
        "documentation": """
## Usage

Use this skill when you need to find information on the web. It's particularly useful for:

- Current events and news
- Technical documentation
- General knowledge queries
- Finding specific websites or resources

## Rate Limits

This skill is subject to rate limiting. Please use responsibly.
        """,
        "examples": [
            {
                "description": "Search for Python documentation",
                "input": {"query": "Python asyncio tutorial", "max_results": 5},
                "output": {
                    "results": [
                        {
                            "title": "asyncio - Python Documentation",
                            "url": "https://docs.python.org/3/library/asyncio.html",
                            "snippet": "asyncio is a library to write concurrent code..."
                        }
                    ]
                }
            }
        ]
    },
    {
        "name": "File Reader",
        "description": "Reads the content of a file from the local filesystem. Supports text files, markdown, JSON, YAML, and other text-based formats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "size": {"type": "integer"},
                "mime_type": {"type": "string"}
            }
        },
        "tags": ["filesystem", "io", "read", "file"],
        "version": "1.0.0",
        "author": "Skills Registry",
        "documentation": """
## Security Note

This skill only has access to files within the allowed directories.
Attempting to read files outside these directories will result in an error.

## Supported Formats

- Plain text (.txt)
- Markdown (.md)
- JSON (.json)
- YAML (.yaml, .yml)
- Source code files
        """
    },
    {
        "name": "Image Generator",
        "description": "Generates an image based on a text prompt using a diffusion model. Returns a URL to the generated image or base64-encoded data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate"
                },
                "style": {
                    "type": "string",
                    "description": "Art style for the image",
                    "enum": ["realistic", "artistic", "cartoon", "sketch"]
                },
                "size": {
                    "type": "string",
                    "description": "Image dimensions",
                    "enum": ["256x256", "512x512", "1024x1024"],
                    "default": "512x512"
                }
            },
            "required": ["prompt"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string"},
                "base64": {"type": "string"},
                "generation_time": {"type": "number"}
            }
        },
        "tags": ["ai", "image", "creative", "generation", "diffusion"],
        "version": "2.0.0",
        "author": "AI Team",
        "documentation": """
## Prompt Tips

For best results:
- Be specific and detailed in your descriptions
- Include style references if desired
- Mention lighting, mood, and atmosphere
- Avoid prohibited content

## Model Information

This skill uses a state-of-the-art diffusion model for image generation.
        """,
        "examples": [
            {
                "description": "Generate a landscape image",
                "input": {
                    "prompt": "A serene mountain landscape at sunset with a lake reflection",
                    "style": "realistic",
                    "size": "1024x1024"
                }
            }
        ]
    },
    {
        "name": "Calculator",
        "description": "Evaluates mathematical expressions. Supports basic arithmetic, trigonometry, logarithms, and common mathematical functions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                },
                "precision": {
                    "type": "integer",
                    "description": "Decimal precision for the result",
                    "default": 10
                }
            },
            "required": ["expression"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "number"},
                "expression_parsed": {"type": "string"}
            }
        },
        "tags": ["math", "utility", "computation", "calculator"],
        "version": "1.0.0",
        "author": "Skills Registry",
        "documentation": """
## Supported Operations

- Basic: +, -, *, /, ^, %
- Functions: sin, cos, tan, log, ln, sqrt, abs
- Constants: pi, e

## Examples

- `2 + 2` => 4
- `sin(pi/2)` => 1
- `sqrt(16)` => 4
        """,
        "examples": [
            {
                "description": "Simple arithmetic",
                "input": {"expression": "2 + 2"},
                "output": {"result": 4}
            },
            {
                "description": "Trigonometry",
                "input": {"expression": "sin(pi/2)"},
                "output": {"result": 1}
            }
        ]
    },
    {
        "name": "Code Executor",
        "description": "Executes code in a sandboxed environment. Supports Python, JavaScript, and shell scripts with safety restrictions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language",
                    "enum": ["python", "javascript", "bash"]
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                }
            },
            "required": ["code", "language"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"},
                "execution_time": {"type": "number"}
            }
        },
        "tags": ["code", "execution", "sandbox", "programming"],
        "version": "1.0.0",
        "author": "Platform Team",
        "documentation": """
## Security

All code is executed in a sandboxed environment with:
- Limited memory and CPU
- No network access
- No filesystem access outside /tmp
- Timeout enforcement

## Limitations

- Maximum execution time: 30 seconds
- Maximum memory: 256MB
- No external dependencies
        """
    },
    {
        "name": "Data Pipeline",
        "description": "Processes and transforms data through configurable pipelines. Supports filtering, mapping, aggregation, and format conversion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Input data array"
                },
                "operations": {
                    "type": "array",
                    "description": "List of operations to apply",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["filter", "map", "reduce", "sort", "group"]
                            },
                            "config": {"type": "object"}
                        }
                    }
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "csv", "table"],
                    "default": "json"
                }
            },
            "required": ["data", "operations"]
        },
        "tags": ["data", "etl", "transform", "pipeline"],
        "version": "1.0.0",
        "author": "Data Team"
    }
]


def register_skills():
    """Register all sample skills."""
    print(f"Connecting to {API_URL}...")
    print()

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
                print(f"Registered: {skill['name']}")
                print(f"  Slug: {result['slug']}")
                print(f"  ID: {result['id']}")
                print()
        except urllib.error.URLError as e:
            print(f"Failed to register {skill['name']}: {e}")


def test_well_known_endpoints():
    """Test RFC well-known endpoints."""
    print("Testing RFC Well-Known Endpoints:")
    print("-" * 40)

    # Test index.json
    try:
        with urllib.request.urlopen(f"{API_URL}/.well-known/skills/index.json") as response:
            data = json.loads(response.read().decode())
            print(f"index.json: {len(data['skills'])} skills found")
            print(f"  RFC Version: {data['version']}")
    except Exception as e:
        print(f"Failed to fetch index.json: {e}")

    # Test SKILL.md for first skill
    try:
        with urllib.request.urlopen(f"{API_URL}/.well-known/skills/web-search/SKILL.md") as response:
            content = response.read().decode()
            print(f"SKILL.md for web-search: {len(content)} bytes")
            print(f"  Content-Type: {response.headers.get('Content-Type')}")
    except Exception as e:
        print(f"Failed to fetch SKILL.md: {e}")

    print()


def test_progressive_disclosure():
    """Test progressive disclosure endpoints."""
    print("Testing Progressive Disclosure:")
    print("-" * 40)

    # Level 1
    try:
        with urllib.request.urlopen(f"{API_URL}/api/v1/skills/level1") as response:
            data = json.loads(response.read().decode())
            print(f"Level 1: {len(data)} skills (minimal metadata)")
            if data:
                print(f"  Example: {data[0]['name']}")
    except Exception as e:
        print(f"Failed Level 1: {e}")

    # Level 2
    try:
        with urllib.request.urlopen(f"{API_URL}/api/v1/skills/calculator/level2") as response:
            data = json.loads(response.read().decode())
            print(f"Level 2 (calculator): Full SKILL.md content")
            print(f"  Version: {data['version']}")
            print(f"  Tags: {data['tags']}")
    except Exception as e:
        print(f"Failed Level 2: {e}")

    # Level 3
    try:
        with urllib.request.urlopen(f"{API_URL}/api/v1/skills/calculator/level3") as response:
            data = json.loads(response.read().decode())
            print(f"Level 3 (calculator): With resources")
            print(f"  Resources: {list(data['resources'].keys())}")
    except Exception as e:
        print(f"Failed Level 3: {e}")

    print()


def test_semantic_search():
    """Test semantic search functionality."""
    queries = [
        "How do I find the capital of France?",
        "I need to read a config file",
        "Calculate 2 + 2",
        "Draw a cat",
        "Run some Python code",
        "Transform and filter data"
    ]

    print("Testing Semantic Search:")
    print("-" * 40)

    for q in queries:
        encoded_q = urllib.parse.quote(q)
        try:
            with urllib.request.urlopen(f"{API_URL}/search?q={encoded_q}&limit=2") as response:
                results = json.loads(response.read().decode())
                print(f"Query: '{q}'")
                for res in results:
                    name = res['skill']['name']
                    score = res['score']
                    print(f"  -> {name} (Score: {score:.4f})")
                print()
        except Exception as e:
            print(f"Search failed: {e}")


def test_health():
    """Test health endpoint."""
    try:
        with urllib.request.urlopen(f"{API_URL}/health") as response:
            data = json.loads(response.read().decode())
            print("Health Check:")
            print(f"  Status: {data['status']}")
            print(f"  Version: {data['version']}")
            print(f"  RFC Version: {data['rfc_version']}")
            print()
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Agent Skills Registry - Seed Script")
    print("RFC-Compliant Skills Discovery")
    print("=" * 50)
    print()

    # Wait for server to be ready
    time.sleep(1)

    test_health()
    register_skills()
    test_well_known_endpoints()
    test_progressive_disclosure()
    test_semantic_search()

    print("=" * 50)
    print("Seeding complete!")
    print("=" * 50)
