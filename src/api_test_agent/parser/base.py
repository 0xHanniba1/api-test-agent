"""Unified data models for parsed API documentation.

All parsers (Swagger, Postman, Markdown) convert their input
into these standard models for downstream processing.
"""

from pydantic import BaseModel


class Param(BaseModel):
    """A single API parameter (query, path, header, or cookie)."""

    name: str
    location: str  # query / path / header / cookie
    required: bool
    param_type: str  # string / integer / boolean / array / object
    description: str = ""
    constraints: dict = {}  # min, max, pattern, enum, etc.


class ApiEndpoint(BaseModel):
    """A single API endpoint with all its metadata."""

    method: str  # GET / POST / PUT / DELETE / PATCH
    path: str  # /api/users/{id}
    summary: str
    parameters: list[Param]
    request_body: dict | None
    responses: dict  # {status_code: {description, schema}}
    auth_required: bool
    tags: list[str]
    content_type: str = "application/json"
