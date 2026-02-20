from pathlib import Path
from api_test_agent.parser.detect import detect_format
from api_test_agent.parser.swagger import parse_openapi

FIXTURES = Path(__file__).parent / "fixtures"


class TestDetectFormat:
    def test_detect_openapi_yaml(self):
        assert detect_format(FIXTURES / "petstore.yaml") == "swagger"

    def test_detect_unknown_format(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# API Docs\nSome text")
        assert detect_format(f) == "markdown"


class TestOpenApiParser:
    def test_parse_petstore_endpoints_count(self):
        endpoints = parse_openapi(FIXTURES / "petstore.yaml")
        assert len(endpoints) == 3

    def test_parse_get_pets(self):
        endpoints = parse_openapi(FIXTURES / "petstore.yaml")
        get_pets = [e for e in endpoints if e.method == "GET" and e.path == "/pets"][0]
        assert get_pets.summary == "List all pets"
        assert len(get_pets.parameters) == 1
        assert get_pets.parameters[0].name == "limit"
        assert get_pets.parameters[0].required is False
        assert get_pets.auth_required is False

    def test_parse_post_pets_has_body(self):
        endpoints = parse_openapi(FIXTURES / "petstore.yaml")
        post_pets = [e for e in endpoints if e.method == "POST"][0]
        assert post_pets.request_body is not None
        assert "name" in post_pets.request_body["properties"]
        assert post_pets.auth_required is True

    def test_parse_path_param(self):
        endpoints = parse_openapi(FIXTURES / "petstore.yaml")
        get_pet = [e for e in endpoints if "{petId}" in e.path][0]
        assert get_pet.parameters[0].location == "path"
        assert get_pet.parameters[0].required is True
