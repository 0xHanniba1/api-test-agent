"""Layered code generator — produces 5-layer API automation project."""

import re
from pathlib import Path

from api_test_agent.llm import LlmClient
from api_test_agent.parser.base import ApiEndpoint

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class LayeredCodeGenerator:
    """Generates pytest code organized into a 5-layer architecture."""

    def __init__(self, model: str | None = None):
        self.client = LlmClient(model=model)

    def _group_by_tag(self, endpoints: list[ApiEndpoint]) -> dict[str, list[ApiEndpoint]]:
        """Group endpoints by their first tag. Untagged endpoints go to 'default'."""
        groups: dict[str, list[ApiEndpoint]] = {}
        for ep in endpoints:
            tag = ep.tags[0] if ep.tags else "default"
            tag = tag.lower().replace(" ", "_")
            groups.setdefault(tag, []).append(ep)
        return groups

    def _render_config(self) -> str:
        return '''import os

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_TOKEN = os.getenv("API_TOKEN", "")
'''

    def _render_client(self) -> str:
        return '''import requests
from .config import BASE_URL, API_TOKEN


class HttpClient:
    def __init__(self, base_url=BASE_URL, token=API_TOKEN):
        self.session = requests.Session()
        self.base_url = base_url
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path, **kwargs):
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path, **kwargs):
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def put(self, path, **kwargs):
        return self.session.put(f"{self.base_url}{path}", **kwargs)

    def delete(self, path, **kwargs):
        return self.session.delete(f"{self.base_url}{path}", **kwargs)

    def patch(self, path, **kwargs):
        return self.session.patch(f"{self.base_url}{path}", **kwargs)
'''

    def _render_requirements(self) -> str:
        return '''requests>=2.28
pytest>=7.0
pyyaml>=6.0
'''

    def _render_conftest(self, tag_names: list[str]) -> str:
        imports = ["import pytest", "from base.client import HttpClient"]
        fixtures = [
            "",
            "",
            "@pytest.fixture",
            "def client():",
            "    return HttpClient()",
        ]
        for tag in tag_names:
            class_name = tag.title().replace("_", "") + "Api"
            imports.append(f"from api.{tag}_api import {class_name}")
            fixtures.extend([
                "",
                "",
                "@pytest.fixture",
                f"def {tag}_api(client):",
                f"    return {class_name}(client)",
            ])
        return "\n".join(imports + fixtures) + "\n"
