"""OpenAPI / Swagger document parser.

Parses OpenAPI 3.x and Swagger 2.0 documents into ApiEndpoint models.
"""

from pathlib import Path

import yaml

from .base import ApiEndpoint, Param


def parse_openapi(file_path: Path) -> list[ApiEndpoint]:
    """Parse an OpenAPI/Swagger file into a list of ApiEndpoint."""
    text = file_path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)

    endpoints = []
    paths = doc.get("paths", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue

            params = _parse_parameters(operation.get("parameters", []))
            request_body = _parse_request_body(operation.get("requestBody"))
            content_type = _detect_content_type(operation.get("requestBody"))
            auth_required = "security" in operation or "security" in doc

            endpoints.append(
                ApiEndpoint(
                    method=method.upper(),
                    path=path,
                    summary=operation.get("summary", ""),
                    parameters=params,
                    request_body=request_body,
                    responses=_parse_responses(operation.get("responses", {})),
                    auth_required=auth_required,
                    tags=operation.get("tags", []),
                    content_type=content_type,
                )
            )

    return endpoints


def _parse_parameters(params: list[dict]) -> list[Param]:
    result = []
    for p in params:
        schema = p.get("schema", {})
        constraints = {}
        for key in ("minimum", "maximum", "minLength", "maxLength", "pattern", "enum"):
            if key in schema:
                constraints[key] = schema[key]

        result.append(
            Param(
                name=p["name"],
                location=p.get("in", "query"),
                required=p.get("required", False),
                param_type=schema.get("type", "string"),
                description=p.get("description", ""),
                constraints=constraints,
            )
        )
    return result


def _parse_request_body(body: dict | None) -> dict | None:
    if not body:
        return None
    content = body.get("content", {})
    for content_type in ("application/json", "multipart/form-data"):
        if content_type in content:
            return content[content_type].get("schema")
    # Fallback: return first available schema
    for ct_data in content.values():
        return ct_data.get("schema")
    return None


def _detect_content_type(body: dict | None) -> str:
    if not body:
        return "application/json"
    content = body.get("content", {})
    if "multipart/form-data" in content:
        return "multipart/form-data"
    return "application/json"


def _parse_responses(responses: dict) -> dict:
    result = {}
    for status_code, resp in responses.items():
        result[str(status_code)] = {"description": resp.get("description", "")}
    return result
