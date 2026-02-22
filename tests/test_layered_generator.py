from api_test_agent.parser.base import ApiEndpoint, Param
from api_test_agent.generator.layered import LayeredCodeGenerator


def _ep(method, path, tags):
    return ApiEndpoint(
        method=method, path=path, summary=f"{method} {path}",
        parameters=[], request_body=None, responses={},
        auth_required=False, tags=tags,
    )


class TestGroupByTag:
    def test_groups_endpoints_by_first_tag(self):
        endpoints = [
            _ep("POST", "/users", ["users"]),
            _ep("GET", "/users/{id}", ["users"]),
            _ep("GET", "/pets", ["pets"]),
        ]
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        groups = gen._group_by_tag(endpoints)
        assert set(groups.keys()) == {"users", "pets"}
        assert len(groups["users"]) == 2
        assert len(groups["pets"]) == 1

    def test_untagged_endpoints_use_default(self):
        endpoints = [_ep("GET", "/health", [])]
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        groups = gen._group_by_tag(endpoints)
        assert "default" in groups


class TestTemplateGeneration:
    def test_generate_config(self):
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        config = gen._render_config()
        assert "API_BASE_URL" in config
        assert "API_TOKEN" in config
        assert "os.getenv" in config

    def test_generate_client(self):
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        client = gen._render_client()
        assert "class HttpClient" in client
        assert "def get(" in client
        assert "def post(" in client
        assert "def put(" in client
        assert "def delete(" in client

    def test_generate_requirements(self):
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        req = gen._render_requirements()
        assert "requests" in req
        assert "pytest" in req
        assert "pyyaml" in req

    def test_generate_conftest(self):
        tag_names = ["users", "pets"]
        gen = LayeredCodeGenerator.__new__(LayeredCodeGenerator)
        conftest = gen._render_conftest(tag_names)
        assert "HttpClient" in conftest
        assert "UsersApi" in conftest
        assert "PetsApi" in conftest
        assert "def users_api" in conftest
        assert "def pets_api" in conftest
