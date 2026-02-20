from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from api_test_agent.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


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
