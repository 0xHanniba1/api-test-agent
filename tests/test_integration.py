"""End-to-end integration tests with mocked LLM calls."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from api_test_agent.cli import main

FIXTURES = Path(__file__).parent / "fixtures"

# Each mock represents LLM output for one endpoint (petstore has 3 endpoints)
MOCK_TC_GET_PETS = """## GET /pets

> List all pets

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-001 | 正常获取宠物列表 | limit=10 | 200 | 返回宠物数组 | P0 |
| TC-002 | 不传参数 | 无 | 200 | 返回默认列表 | P0 |"""

MOCK_TC_POST_PETS = """## POST /pets

> Create a pet

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-003 | 正常创建宠物 | {"name":"Fido"} | 201 | 返回宠物ID | P0 |
| TC-004 | 缺少 name | {} | 400 | 提示 name 必填 | P0 |"""

MOCK_TC_GET_PET_BY_ID = """## GET /pets/{petId}

> Info for a specific pet

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-005 | 正常获取宠物详情 | petId=1 | 200 | 返回宠物详情 | P0 |
| TC-006 | 宠物不存在 | petId=9999 | 404 | 提示宠物不存在 | P0 |"""

MOCK_CONFTEST = '''```python
# conftest.py
import pytest
import os

@pytest.fixture
def base_url():
    return os.getenv("API_BASE_URL", "http://localhost:8080")

@pytest.fixture
def auth_headers():
    token = os.getenv("API_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}
```'''

MOCK_TEST_CODE_1 = '''```python
# test_list_pets.py
import requests

class TestListPets:
    """GET /pets"""
    def test_list_pets_success(self, base_url, auth_headers):
        """TC-001: 正常获取宠物列表"""
        resp = requests.get(f"{base_url}/pets", params={"limit": 10}, headers=auth_headers)
        assert resp.status_code == 200
```'''

MOCK_TEST_CODE_2 = '''```python
# test_create_pet.py
import requests

class TestCreatePet:
    """POST /pets"""
    def test_create_pet_success(self, base_url, auth_headers):
        """TC-003: 正常创建宠物"""
        resp = requests.post(f"{base_url}/pets", json={"name": "Fido"}, headers=auth_headers)
        assert resp.status_code == 201
```'''

MOCK_TEST_CODE_3 = '''```python
# test_show_pet.py
import requests

class TestShowPet:
    """GET /pets/{petId}"""
    def test_show_pet_success(self, base_url, auth_headers):
        """TC-005: 正常获取宠物详情"""
        resp = requests.get(f"{base_url}/pets/1", headers=auth_headers)
        assert resp.status_code == 200
```'''


class TestEndToEnd:
    @patch("api_test_agent.generator.code.LlmClient")
    @patch("api_test_agent.generator.testcase.LlmClient")
    def test_full_pipeline_petstore(self, MockTCLlm, MockCodeLlm, tmp_path):
        # Mock test case generation (one call per endpoint, petstore has 3)
        mock_tc_client = MagicMock()
        mock_tc_client.call.side_effect = [
            MOCK_TC_GET_PETS,
            MOCK_TC_POST_PETS,
            MOCK_TC_GET_PET_BY_ID,
        ]
        MockTCLlm.return_value = mock_tc_client

        # Mock code generation: 1 conftest + 3 test files (one per ## section)
        mock_code_client = MagicMock()
        mock_code_client.call.side_effect = [
            MOCK_CONFTEST,
            MOCK_TEST_CODE_1,
            MOCK_TEST_CODE_2,
            MOCK_TEST_CODE_3,
        ]
        MockCodeLlm.return_value = mock_code_client

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(FIXTURES / "petstore.yaml"),
            "-o", str(output_dir),
        ])

        assert result.exit_code == 0
        assert (output_dir / "testcases.md").exists()
        assert (output_dir / "conftest.py").exists()

        # Verify test cases file has content
        testcases_content = (output_dir / "testcases.md").read_text()
        assert len(testcases_content) > 0
