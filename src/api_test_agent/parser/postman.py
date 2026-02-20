"""Postman Collection v2.1 parser.

Parses Postman exported JSON files into ApiEndpoint models.
"""

import json
from pathlib import Path

from .base import ApiEndpoint, Param


def parse_postman(file_path: Path) -> list[ApiEndpoint]:
    """Parse a Postman Collection v2.1 file into a list of ApiEndpoint."""
    text = file_path.read_text(encoding="utf-8")
    collection = json.loads(text)

    endpoints: list[ApiEndpoint] = []
    _parse_items(collection.get("item", []), endpoints)
    return endpoints


def _parse_items(items: list[dict], endpoints: list[ApiEndpoint]) -> None:
    """Recursively parse items (supports folders)."""
    for item in items:
        if "item" in item:
            _parse_items(item["item"], endpoints)
        elif "request" in item:
            endpoints.append(_parse_request(item))


def _parse_request(item: dict) -> ApiEndpoint:
    req = item["request"]
    method = req["method"].upper()
    url = req.get("url", {})

    path = "/" + "/".join(url.get("path", []))
    params = _parse_query_params(url.get("query", []))
    body = _parse_body(req.get("body"))
    auth_required = _has_auth_header(req.get("header", []))
    tags: list[str] = []

    return ApiEndpoint(
        method=method,
        path=path,
        summary=item.get("name", ""),
        parameters=params,
        request_body=body,
        responses={},
        auth_required=auth_required,
        tags=tags,
    )


def _parse_query_params(query: list[dict]) -> list[Param]:
    return [
        Param(
            name=q["key"],
            location="query",
            required=False,
            param_type="string",
            description=q.get("description", ""),
        )
        for q in query
    ]


def _parse_body(body: dict | None) -> dict | None:
    if not body:
        return None
    if body.get("mode") == "raw":
        try:
            return json.loads(body["raw"])
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def _has_auth_header(headers: list[dict]) -> bool:
    return any(h.get("key", "").lower() == "authorization" for h in headers)
