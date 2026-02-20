from unittest.mock import patch, MagicMock
from api_test_agent.parser.base import Param, ApiEndpoint
from api_test_agent.generator.testcase import TestCaseGenerator

MOCK_LLM_RESPONSE = """## POST /api/users

> Create user

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-001 | 正常创建用户 | {"name":"test","email":"a@b.com"} | 201 | 返回用户ID | P0 |
| TC-002 | 缺少必填字段 name | {"email":"a@b.com"} | 400 | 提示 name 必填 | P0 |
"""


class TestTestCaseGenerator:
    def _make_endpoint(self):
        return ApiEndpoint(
            method="POST",
            path="/api/users",
            summary="Create user",
            parameters=[],
            request_body={
                "type": "object",
                "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                "required": ["name", "email"],
            },
            responses={"201": {"description": "Created"}},
            auth_required=True,
            tags=["users"],
        )

    @patch("api_test_agent.generator.testcase.LlmClient")
    def test_generate_returns_markdown(self, MockLlmClient):
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_LLM_RESPONSE
        MockLlmClient.return_value = mock_client

        gen = TestCaseGenerator(model="test-model")
        result = gen.generate([self._make_endpoint()], depth="quick")

        assert "TC-001" in result
        assert "POST /api/users" in result

    @patch("api_test_agent.generator.testcase.LlmClient")
    def test_generate_calls_llm_with_skills(self, MockLlmClient):
        mock_client = MagicMock()
        mock_client.call.return_value = MOCK_LLM_RESPONSE
        MockLlmClient.return_value = mock_client

        gen = TestCaseGenerator(model="test-model")
        gen.generate([self._make_endpoint()], depth="quick")

        call_args = mock_client.call.call_args
        system_prompt = call_args[1]["system"] if "system" in call_args[1] else call_args[0][0]
        assert "测试" in system_prompt or "test" in system_prompt.lower()
