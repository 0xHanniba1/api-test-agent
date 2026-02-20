from pathlib import Path
from api_test_agent.parser.postman import parse_postman
from api_test_agent.parser.detect import detect_format

FIXTURES = Path(__file__).parent / "fixtures"


class TestDetectPostman:
    def test_detect_postman_format(self):
        assert detect_format(FIXTURES / "sample.postman.json") == "postman"


class TestPostmanParser:
    def test_parse_endpoints_count(self):
        endpoints = parse_postman(FIXTURES / "sample.postman.json")
        assert len(endpoints) == 2

    def test_parse_get_request(self):
        endpoints = parse_postman(FIXTURES / "sample.postman.json")
        get_ep = [e for e in endpoints if e.method == "GET"][0]
        assert get_ep.path == "/api/users"
        assert len(get_ep.parameters) == 2
        assert get_ep.auth_required is False

    def test_parse_post_with_auth(self):
        endpoints = parse_postman(FIXTURES / "sample.postman.json")
        post_ep = [e for e in endpoints if e.method == "POST"][0]
        assert post_ep.path == "/api/users"
        assert post_ep.request_body is not None
        assert post_ep.auth_required is True
