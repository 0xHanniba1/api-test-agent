"""Test case generator — uses LLM + skills to produce test case documents."""

from pathlib import Path

from api_test_agent.llm import LlmClient
from api_test_agent.parser.base import ApiEndpoint
from api_test_agent.skills.loader import select_skills, load_skill_content

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestCaseGenerator:
    """Generates test case Markdown documents from API endpoint definitions."""

    def __init__(self, model: str | None = None):
        self.client = LlmClient(model=model)

    def generate(self, endpoints: list[ApiEndpoint], depth: str = "quick") -> str:
        """Generate test cases for all endpoints, returns Markdown string."""
        results = []
        for endpoint in endpoints:
            result = self._generate_for_endpoint(endpoint, depth)
            results.append(result)
        return "\n\n".join(results)

    def _generate_for_endpoint(self, endpoint: ApiEndpoint, depth: str) -> str:
        skill_names = select_skills(endpoint, depth)
        skill_content = load_skill_content(skill_names)

        prompt_template = (PROMPTS_DIR / "testcase.md").read_text(encoding="utf-8")
        system_prompt = f"{skill_content}\n\n---\n\n{prompt_template}"

        user_prompt = (
            f"请为以下接口生成测试用例，深度级别：{depth}\n\n"
            f"```json\n{endpoint.model_dump_json(indent=2)}\n```"
        )

        return self.client.call(system=system_prompt, user=user_prompt)
