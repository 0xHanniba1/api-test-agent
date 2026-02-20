"""Auto-detect API documentation format."""

import json
from pathlib import Path

import yaml


def detect_format(file_path: Path) -> str:
    """Detect the format of an API documentation file.

    Returns: 'swagger', 'postman', or 'markdown'.
    """
    text = file_path.read_text(encoding="utf-8")

    # Try YAML/JSON parsing
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            if "openapi" in data or "swagger" in data:
                return "swagger"
            if "info" in data and "_postman_id" in data.get("info", {}):
                return "postman"
    except yaml.YAMLError:
        pass

    # Try JSON specifically (for files not parseable as YAML)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if "openapi" in data or "swagger" in data:
                return "swagger"
            if "info" in data and "_postman_id" in data.get("info", {}):
                return "postman"
    except (json.JSONDecodeError, ValueError):
        pass

    return "markdown"
