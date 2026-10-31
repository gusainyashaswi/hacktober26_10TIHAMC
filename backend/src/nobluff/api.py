"""Local API for the first extraction workflow; no repository execution."""

import re
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator
from starlette.types import ASGIApp, Receive, Scope, Send

from nobluff.model import OllamaSettings
from nobluff.model.extraction import MAX_REPORT_CHARS
from nobluff.pipeline import AnalysisService, CapacityError
from nobluff.schemas import AnalysisReport, AnalysisRequest, Contract, Text


class APIAnalysisRequest(AnalysisRequest):
    repository: Text = Field(max_length=250)
    revision: Text = Field(max_length=200)
    comparison_revision: Text | None = Field(default=None, max_length=200)
    report_text: Text = Field(max_length=MAX_REPORT_CHARS)

    @field_validator("repository")
    @classmethod
    def github_repository_only(cls, value: str) -> str:
        if "://" in value:
            url = urlsplit(value)
            if (
                url.scheme != "https"
                or url.netloc.lower() != "github.com"
                or url.query
                or url.fragment
            ):
                raise ValueError(
                    "Use a public GitHub repository URL or owner/repository"
                )
            value = url.path.strip("/")
        value = value.removesuffix(".git")
        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", value
        ):
            raise ValueError("Use owner/repository, not a local path or issue URL")
        if value.split("/")[1] in (".", ".."):
            raise ValueError("Repository name must identify a repository")
        return f"https://github.com/{value}"

    @field_validator("revision", "comparison_revision")
    @classmethod
    def bounded_revision_label(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s\x00-\x1f]{1,200}", value):
            raise ValueError("Revision must be a nonempty label without whitespace")
        return value


class AcceptedAnalysis(Contract):
    id: Text


class BodyLimitMiddleware:
    """Bound the JSON body even when Content-Length is missing or inaccurate."""

    def __init__(self, app: ASGIApp, max_bytes: int = 64_000):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds 64000 bytes."},
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(service: AnalysisService | None = None) -> FastAPI:
    if service is None:
        service = AnalysisService(OllamaSettings.from_env())
    app = FastAPI(
        title="NoBluff local analysis API",
        description="Claim extraction only. Repository loading, evidence assessment and execution are not connected yet.",
    )
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Location", "X-NoBluff-Scope"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        # Pydantic's default errors include submitted input; omit it here.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": list(error["loc"]),
                        "type": error["type"],
                        "msg": error["msg"],
                    }
                    for error in exc.errors()
                ]
            },
        )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "scope": "claim_extraction",
            "model": service.settings.model,
            "model_readiness": "not_checked",
            "repository_loading": False,
            "evidence_assessment": False,
            "verification": False,
        }

    @app.post("/api/analyses", status_code=202, response_model=AcceptedAnalysis)
    def submit(request: APIAnalysisRequest, background: BackgroundTasks):
        try:
            identifier = service.submit(request)
        except CapacityError as exc:
            raise HTTPException(
                status_code=429, detail=str(exc), headers={"Retry-After": "2"}
            ) from exc
        background.add_task(service.run, identifier, request.report_text)
        return JSONResponse(
            status_code=202,
            content={"id": identifier},
            headers={
                "Location": f"/api/analyses/{identifier}",
                "X-NoBluff-Scope": "claim_extraction_only",
            },
        )

    @app.get("/api/analyses/{identifier}", response_model=AnalysisReport)
    def get_report(identifier: str):
        report = service.get(identifier)
        if report is None:
            raise HTTPException(
                status_code=404, detail="Analysis not found in this server process."
            )
        return report

    @app.post("/api/analyses/{identifier}/verification", status_code=501)
    def verification_unavailable(identifier: str):
        if service.get(identifier) is None:
            raise HTTPException(
                status_code=404, detail="Analysis not found in this server process."
            )
        raise HTTPException(
            status_code=501,
            detail="Controlled verification is not connected. No code was executed.",
        )

    return app
