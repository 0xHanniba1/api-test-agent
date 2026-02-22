from api_test_agent.generator.validator import validate_python, validate_yaml, validate_collect, validate_files


class TestValidatePython:
    def test_valid_code(self):
        errors = validate_python({"test_ok.py": "import os\nx = 1\n"})
        assert errors == {}

    def test_syntax_error(self):
        errors = validate_python({"test_bad.py": "def foo(\n"})
        assert "test_bad.py" in errors
        assert "SyntaxError" in errors["test_bad.py"]

    def test_skips_non_python(self):
        errors = validate_python({"data.yaml": "key: value", "test_ok.py": "x = 1"})
        assert errors == {}

    def test_skips_empty_init(self):
        errors = validate_python({"__init__.py": ""})
        assert errors == {}


class TestValidateYaml:
    def test_valid_yaml(self):
        errors = validate_yaml({"users.yaml": "name: test\nage: 20\n"})
        assert errors == {}

    def test_invalid_yaml(self):
        errors = validate_yaml({"bad.yaml": "key: [invalid\n"})
        assert "bad.yaml" in errors

    def test_skips_non_yaml(self):
        errors = validate_yaml({"test.py": "x = 1", "ok.yaml": "a: 1"})
        assert errors == {}


class TestValidateCollect:
    def test_valid_tests_collect(self):
        files = {
            "conftest.py": "import pytest\n\n@pytest.fixture\ndef base_url():\n    return 'http://localhost'\n",
            "test_example.py": "class TestExample:\n    def test_ok(self, base_url):\n        assert True\n",
        }
        errors = validate_collect(files)
        assert errors == {}

    def test_import_error_detected(self):
        files = {
            "test_bad.py": "from nonexistent_module import Foo\n\nclass TestBad:\n    def test_x(self):\n        pass\n",
        }
        errors = validate_collect(files)
        assert len(errors) > 0

    def test_empty_files_skip(self):
        files = {"__init__.py": ""}
        errors = validate_collect(files)
        assert errors == {}


class TestValidateFiles:
    def test_all_valid(self):
        files = {
            "conftest.py": "import pytest\n",
            "test_ok.py": "class TestOk:\n    def test_x(self):\n        assert True\n",
            "data.yaml": "key: value\n",
        }
        errors = validate_files(files)
        assert errors == {}

    def test_python_error_caught(self):
        files = {
            "test_bad.py": "def foo(\n",
            "data.yaml": "key: value\n",
        }
        errors = validate_files(files)
        assert "test_bad.py" in errors

    def test_yaml_error_caught(self):
        files = {
            "test_ok.py": "x = 1\n",
            "bad.yaml": "key: [invalid\n",
        }
        errors = validate_files(files)
        assert "bad.yaml" in errors
