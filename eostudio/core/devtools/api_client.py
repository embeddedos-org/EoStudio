"""REST and GraphQL API client with collection management."""
from __future__ import annotations

import enum
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class HTTPMethod(enum.Enum):
    """HTTP request methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(enum.Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


@dataclass
class AuthConfig:
    """Authentication configuration."""
    auth_type: AuthType = AuthType.NONE
    username: str = ""
    password: str = ""
    token: str = ""
    api_key: str = ""
    api_key_header: str = "X-API-Key"
    oauth2_client_id: str = ""
    oauth2_client_secret: str = ""
    oauth2_token_url: str = ""
    oauth2_scopes: list[str] = field(default_factory=list)


@dataclass
class APIRequest:
    """Definition of an API request."""
    method: HTTPMethod = HTTPMethod.GET
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: Any = None
    auth: AuthConfig | None = None
    timeout: float = 30.0
    name: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "url": self.url,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "timeout": self.timeout,
            "name": self.name,
        }


@dataclass
class APIResponse:
    """API response data."""
    status_code: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    elapsed_ms: float = 0.0
    size_bytes: int = 0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def json(self) -> Any:
        if isinstance(self.body, (dict, list)):
            return self.body
        if isinstance(self.body, str):
            return json.loads(self.body)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body,
            "elapsed_ms": self.elapsed_ms,
            "size_bytes": self.size_bytes,
        }


@dataclass
class APIEnvironment:
    """Named set of variables for an API environment."""
    name: str = "default"
    variables: dict[str, str] = field(default_factory=dict)

    def resolve(self, text: str) -> str:
        """Replace {{var}} placeholders with environment values."""
        for key, val in self.variables.items():
            text = text.replace("{{" + key + "}}", val)
        return text


@dataclass
class APICollection:
    """Named collection of saved API requests."""
    name: str = ""
    description: str = ""
    requests: list[APIRequest] = field(default_factory=list)
    environments: list[APIEnvironment] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "requests": [r.to_dict() for r in self.requests],
            "environments": [{"name": e.name, "variables": e.variables} for e in self.environments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APICollection:
        col = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            id=data.get("id", uuid.uuid4().hex[:12]),
        )
        for rd in data.get("requests", []):
            col.requests.append(
                APIRequest(
                    method=HTTPMethod(rd.get("method", "GET")),
                    url=rd.get("url", ""),
                    headers=rd.get("headers", {}),
                    params=rd.get("params", {}),
                    body=rd.get("body"),
                    timeout=rd.get("timeout", 30.0),
                    name=rd.get("name", ""),
                )
            )
        for ed in data.get("environments", []):
            col.environments.append(APIEnvironment(name=ed.get("name", ""), variables=ed.get("variables", {})))
        return col


def _get_httpx():
    """Lazy import httpx."""
    try:
        import httpx
        return httpx
    except ImportError:
        raise ImportError(
            "httpx is required for API client functionality. Install it with: pip install httpx"
        )


class APIClient:
    """REST and GraphQL API client."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self._history: list[tuple[APIRequest, APIResponse]] = []
        self._environment: APIEnvironment | None = None

    def set_environment(self, env: APIEnvironment) -> None:
        self._environment = env

    def _resolve(self, text: str) -> str:
        if self._environment:
            return self._environment.resolve(text)
        return text

    def _build_url(self, url: str) -> str:
        url = self._resolve(url)
        if url.startswith(("http://", "https://")):
            return url
        return f"{self.base_url}/{url.lstrip('/')}" if self.base_url else url

    def _apply_auth(self, headers: dict[str, str], auth: AuthConfig | None) -> tuple[dict[str, str], Any]:
        """Apply auth config to headers. Returns (headers, httpx_auth)."""
        httpx_auth = None
        if auth is None or auth.auth_type == AuthType.NONE:
            return headers, httpx_auth

        httpx = _get_httpx()

        if auth.auth_type == AuthType.BASIC:
            httpx_auth = httpx.BasicAuth(username=auth.username, password=auth.password)
        elif auth.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {self._resolve(auth.token)}"
        elif auth.auth_type == AuthType.API_KEY:
            headers[auth.api_key_header] = self._resolve(auth.api_key)
        return headers, httpx_auth

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def request(self, req: APIRequest) -> APIResponse:
        """Execute an API request and return the response."""
        httpx = _get_httpx()

        url = self._build_url(req.url)
        headers = {k: self._resolve(v) for k, v in req.headers.items()}
        params = {k: self._resolve(v) for k, v in req.params.items()}

        headers, auth_obj = self._apply_auth(headers, req.auth)

        body_kwargs: dict[str, Any] = {}
        if req.body is not None:
            if isinstance(req.body, (dict, list)):
                body_kwargs["json"] = req.body
                headers.setdefault("Content-Type", "application/json")
            elif isinstance(req.body, str):
                body_kwargs["content"] = req.body
            else:
                body_kwargs["content"] = str(req.body)

        start = time.monotonic()
        with httpx.Client(timeout=req.timeout) as client:
            resp = client.request(
                method=req.method.value,
                url=url,
                headers=headers,
                params=params or None,
                auth=auth_obj,
                **body_kwargs,
            )
        elapsed = (time.monotonic() - start) * 1000.0

        try:
            resp_body = resp.json()
        except (json.JSONDecodeError, ValueError):
            resp_body = resp.text

        api_resp = APIResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp_body,
            elapsed_ms=round(elapsed, 2),
            size_bytes=len(resp.content),
        )
        self._history.append((req, api_resp))
        return api_resp

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get(self, url: str, **kwargs: Any) -> APIResponse:
        return self.request(APIRequest(method=HTTPMethod.GET, url=url, **kwargs))

    def post(self, url: str, **kwargs: Any) -> APIResponse:
        return self.request(APIRequest(method=HTTPMethod.POST, url=url, **kwargs))

    def put(self, url: str, **kwargs: Any) -> APIResponse:
        return self.request(APIRequest(method=HTTPMethod.PUT, url=url, **kwargs))

    def patch(self, url: str, **kwargs: Any) -> APIResponse:
        return self.request(APIRequest(method=HTTPMethod.PATCH, url=url, **kwargs))

    def delete(self, url: str, **kwargs: Any) -> APIResponse:
        return self.request(APIRequest(method=HTTPMethod.DELETE, url=url, **kwargs))

    # ------------------------------------------------------------------
    # GraphQL
    # ------------------------------------------------------------------

    def graphql(self, url: str, query: str, variables: dict[str, Any] | None = None, **kwargs: Any) -> APIResponse:
        """Execute a GraphQL query."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        return self.request(
            APIRequest(method=HTTPMethod.POST, url=url, body=payload, **kwargs)
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict[str, Any]]:
        return [
            {"request": req.to_dict(), "response": resp.to_dict()}
            for req, resp in self._history
        ]

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def save_collection(self, collection: APICollection, path: str) -> None:
        """Save a collection to a JSON file."""
        Path(path).write_text(json.dumps(collection.to_dict(), indent=2))

    def load_collection(self, path: str) -> APICollection:
        """Load a collection from a JSON file."""
        data = json.loads(Path(path).read_text())
        return APICollection.from_dict(data)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_postman(self, path: str) -> APICollection:
        """Import a Postman collection v2.1 JSON file."""
        raw = json.loads(Path(path).read_text())
        info = raw.get("info", {})
        col = APICollection(name=info.get("name", "Imported"), description=info.get("description", ""))

        def _parse_items(items: list[dict]) -> None:
            for item in items:
                if "item" in item:
                    _parse_items(item["item"])
                    continue
                req_data = item.get("request", {})
                method_str = req_data.get("method", "GET")
                url_data = req_data.get("url", {})
                if isinstance(url_data, str):
                    url = url_data
                else:
                    url = url_data.get("raw", "")

                headers: dict[str, str] = {}
                for h in req_data.get("header", []):
                    headers[h.get("key", "")] = h.get("value", "")

                body = None
                body_data = req_data.get("body", {})
                if body_data.get("mode") == "raw":
                    raw_body = body_data.get("raw", "")
                    try:
                        body = json.loads(raw_body)
                    except (json.JSONDecodeError, ValueError):
                        body = raw_body

                col.requests.append(
                    APIRequest(
                        method=HTTPMethod(method_str.upper()),
                        url=url,
                        headers=headers,
                        body=body,
                        name=item.get("name", ""),
                    )
                )

        _parse_items(raw.get("item", []))
        return col

    def import_openapi(self, path: str) -> APICollection:
        """Import an OpenAPI 3.x JSON/YAML spec (JSON only for stdlib)."""
        raw = json.loads(Path(path).read_text())
        title = raw.get("info", {}).get("title", "OpenAPI Import")
        col = APICollection(name=title)
        servers = raw.get("servers", [])
        base = servers[0].get("url", "") if servers else ""

        for route, methods in raw.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                    continue
                col.requests.append(
                    APIRequest(
                        method=HTTPMethod(method.upper()),
                        url=f"{base}{route}",
                        name=details.get("summary", f"{method.upper()} {route}"),
                        description=details.get("description", ""),
                    )
                )
        return col

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def generate_code(self, req: APIRequest, language: str = "python") -> str:
        """Generate sample code for a request in the given language."""
        url = self._build_url(req.url)
        if language == "python":
            lines = [
                "import httpx",
                "",
                f'resp = httpx.{req.method.value.lower()}(',
                f'    "{url}",',
            ]
            if req.headers:
                lines.append(f"    headers={json.dumps(req.headers)},")
            if req.params:
                lines.append(f"    params={json.dumps(req.params)},")
            if req.body is not None:
                lines.append(f"    json={json.dumps(req.body)},")
            lines.append(f"    timeout={req.timeout},")
            lines.append(")")
            lines.append("print(resp.status_code, resp.json())")
            return "\n".join(lines)

        if language == "curl":
            parts = [f"curl -X {req.method.value} '{url}'"]
            for k, v in req.headers.items():
                parts.append(f"  -H '{k}: {v}'")
            if req.body is not None:
                parts.append(f"  -d '{json.dumps(req.body)}'")
            return " \\\n".join(parts)

        if language in ("javascript", "js", "typescript", "ts"):
            opts: dict[str, Any] = {"method": req.method.value}
            if req.headers:
                opts["headers"] = req.headers
            if req.body is not None:
                opts["body"] = "JSON.stringify(body)"
            lines = [
                f'const resp = await fetch("{url}", {json.dumps(opts, indent=2)});',
                "const data = await resp.json();",
                "console.log(data);",
            ]
            return "\n".join(lines)

        return f"// Code generation for '{language}' is not yet supported."
