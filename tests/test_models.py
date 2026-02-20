from api_test_agent.parser.base import Param, ApiEndpoint


class TestParam:
    def test_create_required_param(self):
        p = Param(name="id", location="path", required=True, param_type="integer")
        assert p.name == "id"
        assert p.required is True
        assert p.description == ""
        assert p.constraints == {}

    def test_create_param_with_constraints(self):
        p = Param(
            name="age",
            location="query",
            required=False,
            param_type="integer",
            description="User age",
            constraints={"min": 0, "max": 150},
        )
        assert p.constraints["min"] == 0


class TestApiEndpoint:
    def test_create_minimal_endpoint(self):
        ep = ApiEndpoint(
            method="GET",
            path="/api/users",
            summary="List users",
            parameters=[],
            request_body=None,
            responses={"200": {"description": "Success"}},
            auth_required=False,
            tags=["users"],
        )
        assert ep.method == "GET"
        assert ep.content_type == "application/json"

    def test_create_post_endpoint_with_body(self):
        ep = ApiEndpoint(
            method="POST",
            path="/api/users",
            summary="Create user",
            parameters=[],
            request_body={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name", "email"],
            },
            responses={"201": {"description": "Created"}},
            auth_required=True,
            tags=["users"],
        )
        assert ep.request_body is not None
        assert ep.auth_required is True

    def test_endpoint_serialization_roundtrip(self):
        ep = ApiEndpoint(
            method="DELETE",
            path="/api/users/{id}",
            summary="Delete user",
            parameters=[
                Param(name="id", location="path", required=True, param_type="integer")
            ],
            request_body=None,
            responses={"204": {"description": "Deleted"}},
            auth_required=True,
            tags=["users"],
        )
        data = ep.model_dump()
        ep2 = ApiEndpoint(**data)
        assert ep2.path == "/api/users/{id}"
        assert len(ep2.parameters) == 1
