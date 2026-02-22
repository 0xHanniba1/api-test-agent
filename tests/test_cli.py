from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from api_test_agent.cli import main, _filter_endpoints
from api_test_agent.parser.base import ApiEndpoint
from api_test_agent.generator.layered import LayeredCodeGenerator

FIXTURES = Path(__file__).parent / "fixtures"


def _make_endpoint(method: str, path: str) -> ApiEndpoint:
    return ApiEndpoint(
        method=method,
        path=path,
        summary="",
        parameters=[],
        request_body=None,
        responses={},
        auth_required=False,
        tags=[],
    )


class TestCliGenCases:
    @patch("api_test_agent.cli.TestCaseGenerator")
    def test_gen_cases_with_swagger(self, MockGen, tmp_path):
        mock_gen = MagicMock()
        mock_gen.generate.return_value = "## GET /pets\n| TC-001 | ... |"
        MockGen.return_value = mock_gen

        output_file = tmp_path / "cases.md"
        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-cases", str(FIXTURES / "petstore.yaml"),
            "-o", str(output_file),
        ])

        assert result.exit_code == 0
        assert output_file.exists()
        mock_gen.generate.assert_called_once()


class TestCliGenCode:
    @patch("api_test_agent.cli.CodeGenerator")
    def test_gen_code_from_markdown(self, MockGen, tmp_path):
        # Create input test cases file
        cases_file = tmp_path / "cases.md"
        cases_file.write_text("## POST /api/users\n| TC-001 | test | ... |")

        mock_gen = MagicMock()
        mock_gen.generate.return_value = {
            "conftest.py": "# conftest",
            "test_users.py": "# test code",
        }
        MockGen.return_value = mock_gen

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-code", str(cases_file),
            "-o", str(output_dir),
        ])

        assert result.exit_code == 0
        assert (output_dir / "conftest.py").exists()
        assert (output_dir / "test_users.py").exists()


class TestCliRun:
    @patch("api_test_agent.cli.CodeGenerator")
    @patch("api_test_agent.cli.TestCaseGenerator")
    def test_run_full_pipeline(self, MockTCGen, MockCodeGen, tmp_path):
        mock_tc = MagicMock()
        mock_tc.generate.return_value = "## GET /pets\n| TC-001 | ... |"
        MockTCGen.return_value = mock_tc

        mock_code = MagicMock()
        mock_code.generate.return_value = {
            "conftest.py": "# conftest",
            "test_pets.py": "# tests",
        }
        MockCodeGen.return_value = mock_code

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(FIXTURES / "petstore.yaml"),
            "-o", str(output_dir),
        ])

        assert result.exit_code == 0
        mock_tc.generate.assert_called_once()
        mock_code.generate.assert_called_once()


class TestFilterEndpoints:
    def test_filter_by_method_and_path(self):
        endpoints = [
            _make_endpoint("GET", "/pets"),
            _make_endpoint("POST", "/pets"),
            _make_endpoint("GET", "/users"),
        ]
        result = _filter_endpoints(endpoints, ("POST /pets",))
        assert len(result) == 1
        assert result[0].method == "POST"
        assert result[0].path == "/pets"

    def test_filter_by_path_only(self):
        endpoints = [
            _make_endpoint("GET", "/pets"),
            _make_endpoint("POST", "/pets/123"),
            _make_endpoint("GET", "/users"),
        ]
        result = _filter_endpoints(endpoints, ("/pets/*",))
        assert len(result) == 1
        assert result[0].path == "/pets/123"

    def test_filter_no_match(self):
        endpoints = [
            _make_endpoint("GET", "/pets"),
            _make_endpoint("POST", "/pets"),
        ]
        result = _filter_endpoints(endpoints, ("DELETE /orders",))
        assert len(result) == 0


class TestAppendMode:
    @patch("api_test_agent.cli.TestCaseGenerator")
    def test_gen_cases_append(self, MockGen, tmp_path):
        mock_gen = MagicMock()
        mock_gen.generate.return_value = "## NEW CONTENT"
        MockGen.return_value = mock_gen

        output_file = tmp_path / "cases.md"
        output_file.write_text("## EXISTING CONTENT", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-cases", str(FIXTURES / "petstore.yaml"),
            "-o", str(output_file),
            "--append",
        ])

        assert result.exit_code == 0
        content = output_file.read_text(encoding="utf-8")
        assert "## EXISTING CONTENT" in content
        assert "## NEW CONTENT" in content

    @patch("api_test_agent.cli.CodeGenerator")
    def test_gen_code_append_skips_existing(self, MockGen, tmp_path):
        mock_gen = MagicMock()
        mock_gen.generate.return_value = {
            "conftest.py": "# new conftest",
            "test_pets.py": "# new test",
        }
        MockGen.return_value = mock_gen

        cases_file = tmp_path / "cases.md"
        cases_file.write_text("## POST /pets\n| TC-001 | test |")

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        existing = output_dir / "conftest.py"
        existing.write_text("# original conftest", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-code", str(cases_file),
            "-o", str(output_dir),
            "--append",
        ])

        assert result.exit_code == 0
        assert existing.read_text(encoding="utf-8") == "# original conftest"
        assert (output_dir / "test_pets.py").read_text(encoding="utf-8") == "# new test"


class TestCliGenCodeLayered:
    @patch("api_test_agent.cli.LayeredCodeGenerator")
    def test_gen_code_layered_requires_doc(self, MockGen, tmp_path):
        """--arch layered requires --doc for endpoint info."""
        cases_file = tmp_path / "cases.md"
        cases_file.write_text("## POST /api/users\n| TC-001 | test | ... |")

        mock_gen = MagicMock()
        mock_gen.generate.return_value = {
            "base/config.py": "# config",
            "tests/test_users.py": "# test",
        }
        MockGen.return_value = mock_gen

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-code", str(cases_file),
            "-o", str(output_dir),
            "--arch", "layered",
            "--doc", str(FIXTURES / "petstore.yaml"),
        ])

        assert result.exit_code == 0
        MockGen.assert_called_once()

    @patch("api_test_agent.cli.LayeredCodeGenerator")
    def test_gen_code_layered_without_doc_fails(self, MockGen, tmp_path):
        """--arch layered without --doc should error."""
        cases_file = tmp_path / "cases.md"
        cases_file.write_text("## POST /api/users\n| TC-001 | test | ... |")

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "gen-code", str(cases_file),
            "-o", str(output_dir),
            "--arch", "layered",
        ])

        assert result.exit_code != 0
        assert "--doc" in result.output


class TestCliRunLayered:
    @patch("api_test_agent.cli.LayeredCodeGenerator")
    @patch("api_test_agent.cli.TestCaseGenerator")
    def test_run_layered(self, MockTCGen, MockCodeGen, tmp_path):
        mock_tc = MagicMock()
        mock_tc.generate.return_value = "## GET /pets\n| TC-001 | ... |"
        MockTCGen.return_value = mock_tc

        mock_code = MagicMock()
        mock_code.generate.return_value = {
            "base/config.py": "# config",
            "tests/test_pets.py": "# tests",
        }
        MockCodeGen.return_value = mock_code

        output_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(FIXTURES / "petstore.yaml"),
            "-o", str(output_dir),
            "--arch", "layered",
        ])

        assert result.exit_code == 0
        mock_tc.generate.assert_called_once()
        mock_code.generate.assert_called_once()
