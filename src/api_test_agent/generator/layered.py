"""Layered code generator — produces 5-layer API automation project."""

import re
from pathlib import Path

import click

from api_test_agent.generator.validator import validate_files
from api_test_agent.llm import LlmClient
from api_test_agent.parser.base import ApiEndpoint

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

MAX_RETRIES = 2


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

    def _render_jenkinsfile(self) -> str:
        return '''pipeline {
    agent any

    parameters {
        choice(name: 'ENV', choices: ['dev', 'staging', 'prod'], description: '选择测试环境')
    }

    environment {
        API_BASE_URL = "${params.ENV == 'prod' ? 'https://api.example.com' : params.ENV == 'staging' ? 'https://staging-api.example.com' : 'http://dev-api.example.com'}"
        API_TOKEN = credentials('api-token')
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Test') {
            steps {
                sh 'pytest tests/ -v --junitxml=reports/junit.xml'
            }
        }
    }

    post {
        always {
            junit 'reports/*.xml'
        }
    }
}
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

    # -- section extraction ---------------------------------------------------

    def _split_sections(self, markdown: str) -> list[str]:
        """Split Markdown into sections by ## headers."""
        sections = re.split(r"(?=^## )", markdown, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip() and s.strip().startswith("##")]

    def _extract_sections_for_endpoints(self, testcases_md: str, endpoints: list[ApiEndpoint]) -> str:
        """Extract testcase sections that match the given endpoints."""
        all_sections = self._split_sections(testcases_md)
        matching = []
        for section in all_sections:
            header = section.split("\n")[0]
            for ep in endpoints:
                if re.search(rf"\b{ep.method}\b", header) and ep.path in header:
                    matching.append(section)
                    break
        return "\n\n".join(matching)

    # -- orchestration --------------------------------------------------------

    def generate(self, testcases_md: str, endpoints: list[ApiEndpoint]) -> dict[str, str]:
        """Generate all files for the layered architecture.

        Returns dict of {filepath: content} with paths like 'base/config.py'.
        """
        files: dict[str, str] = {}
        groups = self._group_by_tag(endpoints)
        tag_names = sorted(groups.keys())

        # Static: base layer
        files["base/__init__.py"] = ""
        files["base/config.py"] = self._render_config()
        files["base/client.py"] = self._render_client()

        # Static: requirements + Jenkinsfile
        files["requirements.txt"] = self._render_requirements()
        files["Jenkinsfile"] = self._render_jenkinsfile()

        # Init files for other layers
        files["api/__init__.py"] = ""
        files["services/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # Dynamic: per-tag generation
        for tag, tag_endpoints in groups.items():
            testcases_section = self._extract_sections_for_endpoints(testcases_md, tag_endpoints)

            # API layer
            api_filename, api_code = self._generate_api_layer(tag, tag_endpoints)
            files[f"api/{api_filename}"] = api_code

            # Data layer
            data_filename, data_content = self._generate_data_layer(tag, testcases_section)
            files[f"data/{data_filename}"] = data_content

            # Services layer
            svc_filename, svc_code = self._generate_services_layer(tag, tag_endpoints, api_code)
            files[f"services/{svc_filename}"] = svc_code

            # Tests layer
            test_filename, test_code = self._generate_tests_layer(tag, testcases_section, api_code, data_content)
            files[f"tests/{test_filename}"] = test_code

        # Static: conftest (needs tag_names for fixtures)
        files["tests/conftest.py"] = self._render_conftest(tag_names)

        # Validate and retry
        for attempt in range(MAX_RETRIES + 1):
            errors = validate_files(files)
            if not errors:
                break
            if attempt < MAX_RETRIES:
                click.echo(f"  Validation errors (attempt {attempt + 1}), retrying...")
                files = self._retry_failed(files, errors)
            else:
                click.echo(f"  Validation errors after {MAX_RETRIES} retries:")
                for fname, err in errors.items():
                    click.echo(f"    {fname}: {err}")

        return files

    # -- shared helpers -------------------------------------------------------

    def _extract_code(self, response: str, lang: str = "python") -> str:
        """Extract code from markdown code block."""
        pattern = rf"```{lang}\s*\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def _extract_filename(self, code: str, default: str) -> str:
        """Extract filename from first-line comment like '# users_api.py'."""
        first_line = code.split("\n")[0]
        match = re.search(r"#\s*(\S+\.\w+)", first_line)
        return match.group(1) if match else default

    def _retry_failed(self, files: dict[str, str], errors: dict[str, str]) -> dict[str, str]:
        """Re-generate files that failed validation."""
        for filepath, error_msg in errors.items():
            if filepath == "_collect" or filepath not in files:
                continue
            if filepath.endswith(".py"):
                response = self.client.call(
                    system="你是一个代码修复助手。只输出一个 ```python 代码块，不要任何解释。",
                    user=(
                        f"请修复以下 Python 代码的错误并重新生成。\n\n"
                        f"错误信息：{error_msg}\n\n"
                        f"原始代码：\n```python\n{files[filepath]}\n```"
                    ),
                )
                files[filepath] = self._extract_code(response, "python")
            elif filepath.endswith((".yaml", ".yml")):
                response = self.client.call(
                    system="你是一个代码修复助手。只输出一个 ```yaml 代码块，不要任何解释。",
                    user=(
                        f"请修复以下 YAML 文件的格式错误并重新生成。\n\n"
                        f"错误信息：{error_msg}\n\n"
                        f"原始内容：\n```yaml\n{files[filepath]}\n```"
                    ),
                )
                files[filepath] = self._extract_code(response, "yaml")
        return files

    # -- LLM-based layer generation -------------------------------------------

    def _generate_api_layer(self, tag: str, endpoints: list[ApiEndpoint]) -> tuple[str, str]:
        """Generate API wrapper class for a tag group. Returns (filename, code)."""
        prompt = (PROMPTS_DIR / "layered_api.md").read_text(encoding="utf-8")
        endpoints_json = "\n".join(ep.model_dump_json(indent=2) for ep in endpoints)
        response = self.client.call(
            system=prompt,
            user=f"为 tag '{tag}' 下的以下接口生成封装类：\n\n{endpoints_json}",
        )
        code = self._extract_code(response, "python")
        filename = self._extract_filename(code, f"{tag}_api.py")
        return filename, code

    def _generate_data_layer(self, tag: str, testcases_section: str) -> tuple[str, str]:
        """Generate YAML test data file for a tag group. Returns (filename, content)."""
        prompt = (PROMPTS_DIR / "layered_data.md").read_text(encoding="utf-8")
        response = self.client.call(
            system=prompt,
            user=f"为 tag '{tag}' 从以下测试用例中提取测试数据：\n\n{testcases_section}",
        )
        content = self._extract_code(response, "yaml")
        filename = self._extract_filename(content, f"{tag}.yaml")
        return filename, content

    def _generate_services_layer(self, tag: str, endpoints: list[ApiEndpoint], api_code: str) -> tuple[str, str]:
        """Generate business flow class for a tag group. Returns (filename, code)."""
        prompt = (PROMPTS_DIR / "layered_services.md").read_text(encoding="utf-8")
        endpoints_json = "\n".join(ep.model_dump_json(indent=2) for ep in endpoints)
        response = self.client.call(
            system=prompt,
            user=(
                f"为 tag '{tag}' 生成业务编排类。\n\n"
                f"已有的接口封装类：\n```python\n{api_code}\n```\n\n"
                f"接口定义：\n{endpoints_json}"
            ),
        )
        code = self._extract_code(response, "python")
        filename = self._extract_filename(code, f"{tag}_flow.py")
        return filename, code

    def _generate_tests_layer(self, tag: str, testcases_section: str, api_code: str, data_content: str) -> tuple[str, str]:
        """Generate test file for a tag group. Returns (filename, code)."""
        prompt = (PROMPTS_DIR / "layered_tests.md").read_text(encoding="utf-8")
        response = self.client.call(
            system=prompt,
            user=(
                f"为 tag '{tag}' 生成测试代码。\n\n"
                f"测试用例：\n{testcases_section}\n\n"
                f"接口封装类：\n```python\n{api_code}\n```\n\n"
                f"测试数据文件 ({tag}.yaml)：\n```yaml\n{data_content}\n```"
            ),
        )
        code = self._extract_code(response, "python")
        filename = self._extract_filename(code, f"test_{tag}.py")
        return filename, code
