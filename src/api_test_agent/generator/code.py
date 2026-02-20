"""Code generator — converts test case documents into pytest+requests code."""

import re
from pathlib import Path

from api_test_agent.llm import LlmClient

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class CodeGenerator:
    """Generates pytest + requests code files from test case Markdown documents."""

    def __init__(self, model: str | None = None):
        self.client = LlmClient(model=model)

    def generate(self, testcases_markdown: str) -> dict[str, str]:
        """Generate code files from test case Markdown.

        Returns a dict of {filename: code_content}.
        """
        files = {}

        # Generate conftest.py
        conftest = self._generate_conftest()
        files["conftest.py"] = conftest

        # Split test cases by endpoint sections and generate code for each
        sections = self._split_sections(testcases_markdown)
        for section in sections:
            filename, code = self._generate_test_file(section)
            if filename and code:
                files[filename] = code

        return files

    def _generate_conftest(self) -> str:
        prompt_template = (PROMPTS_DIR / "code.md").read_text(encoding="utf-8")
        response = self.client.call(
            system=prompt_template,
            user="Generate only the conftest.py file with base_url and auth_headers fixtures.",
        )
        return self._extract_code(response)

    def _generate_test_file(self, section: str) -> tuple[str, str]:
        prompt_template = (PROMPTS_DIR / "code.md").read_text(encoding="utf-8")
        response = self.client.call(
            system=prompt_template,
            user=(
                "Generate a single pytest test file for the following test cases. "
                "Include the filename as a comment on the first line.\n\n"
                f"{section}"
            ),
        )
        code = self._extract_code(response)
        filename = self._extract_filename(code)
        return filename, code

    def _split_sections(self, markdown: str) -> list[str]:
        """Split Markdown into sections by ## headers."""
        sections = re.split(r"(?=^## )", markdown, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip() and s.strip().startswith("##")]

    def _extract_code(self, response: str) -> str:
        """Extract Python code from Markdown code blocks."""
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def _extract_filename(self, code: str) -> str:
        """Extract filename from first-line comment like '# test_xxx.py'."""
        first_line = code.split("\n")[0]
        match = re.search(r"(test_\w+\.py|conftest\.py)", first_line)
        if match:
            return match.group(1)
        return "test_generated.py"
