from unittest.mock import patch, MagicMock
from api_test_agent.generator.code import CodeGenerator

SAMPLE_TESTCASES = """## POST /api/users

> Create user

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-001 | 正常创建用户 | {"name":"test","email":"a@b.com"} | 201 | 返回用户ID | P0 |
| TC-002 | 缺少必填字段 name | {"email":"a@b.com"} | 400 | 提示 name 必填 | P0 |
"""

MOCK_CODE_RESPONSE = '''```python
# test_create_user.py
import requests


class TestCreateUser:
    """POST /api/users"""

    def test_create_user_success(self, base_url, auth_headers):
        """TC-001: 正常创建用户"""
        resp = requests.post(
            f"{base_url}/api/users",
            json={"name": "test", "email": "a@b.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
```
'''

MOCK_CONFTEST_RESPONSE = '''```python
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
```
'''


class TestCodeGenerator:
    @patch("api_test_agent.generator.code.LlmClient")
    def test_generate_returns_file_dict(self, MockLlmClient):
        mock_client = MagicMock()
        mock_client.call.side_effect = [MOCK_CONFTEST_RESPONSE, MOCK_CODE_RESPONSE]
        MockLlmClient.return_value = mock_client

        gen = CodeGenerator(model="test-model")
        files = gen.generate(SAMPLE_TESTCASES)

        assert isinstance(files, dict)
        assert "conftest.py" in files
        assert any("test_" in name for name in files)

    @patch("api_test_agent.generator.code.LlmClient")
    def test_generated_code_contains_class(self, MockLlmClient):
        mock_client = MagicMock()
        mock_client.call.side_effect = [MOCK_CONFTEST_RESPONSE, MOCK_CODE_RESPONSE]
        MockLlmClient.return_value = mock_client

        gen = CodeGenerator(model="test-model")
        files = gen.generate(SAMPLE_TESTCASES)

        test_files = {k: v for k, v in files.items() if k.startswith("test_")}
        assert len(test_files) > 0
        for content in test_files.values():
            assert "class Test" in content
