"""Repository-once workflow; no browser credentials or arbitrary host paths."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import Field

from nobluff.github import GitHubError
from nobluff.pipeline import CapacityError
from nobluff.schemas import AnalysisRequest, Contract


class ConnectRepository(Contract):
    repository: str = Field(min_length=1, max_length=250)


def workspace_router(service, store, github):
    router = APIRouter(prefix="/api")

    def available():
        if store is None:
            raise HTTPException(503, "Persistent workspace is not configured.")

    def repository(identifier):
        available()
        record = store.repository(identifier)
        if not record:
            raise HTTPException(404, "Connected repository not found.")
        return record

    def call(action):
        try:
            return action()
        except GitHubError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        except (KeyError, TypeError) as exc:
            raise HTTPException(502, "GitHub returned incomplete metadata.") from exc

    @router.get("/repositories")
    def repositories():
        available()
        return {"items": store.repositories()}

    @router.post("/repositories", status_code=201)
    def connect(request: ConnectRepository):
        available()
        from nobluff.api import APIAnalysisRequest

        try:
            url = APIAnalysisRequest.github_repository_only(request.repository)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        existing = store.repositories()
        if len(existing) >= 20 and not any(
            r["url"].lower() == url.lower() for r in existing
        ):
            raise HTTPException(
                409, "Disconnect a repository before adding more than 20."
            )
        metadata = call(
            lambda: github.repository(url.removeprefix("https://github.com/"))
        )
        return store.connect(metadata)

    @router.delete("/repositories/{identifier}", status_code=204)
    def disconnect(identifier: int):
        repository(identifier)
        store.disconnect(identifier)

    @router.get("/repositories/{identifier}/pulls")
    def pulls(identifier: int, page: int = Query(default=1, ge=1, le=100)):
        record = repository(identifier)
        return call(lambda: github.pulls(record["full_name"], page))

    @router.get("/repositories/{identifier}/pulls/{number}")
    def pull(identifier: int, number: int):
        if number < 1:
            raise HTTPException(422, "PR number must be positive.")
        record = repository(identifier)
        pr = call(lambda: github.pull(record["full_name"], number))
        pr["history"] = [
            r
            for r in store.history(record["url"])
            if r["context"].get("pr_number") == number
        ]
        for item in pr["history"]:
            item["outdated"] = item["context"].get("head_sha") != pr["head_sha"]
        return pr

    @router.post("/repositories/{identifier}/pulls/{number}/analyses", status_code=202)
    def analyse_pull(identifier: int, number: int, background: BackgroundTasks):
        if number < 1:
            raise HTTPException(422, "PR number must be positive.")
        record = repository(identifier)
        pr = call(lambda: github.pull(record["full_name"], number))
        comparison = call(lambda: github.comparison(record["full_name"], pr))
        text = pr["title"] + "\n\n" + pr["body"]
        if len(text) > 12000:
            raise HTTPException(
                422,
                "This PR description exceeds the model input limit; use a focused manual investigation.",
            )
        request = AnalysisRequest(
            repository=record["url"],
            revision=comparison["original_revision"],
            comparison_revision=comparison["head_revision"],
            source_revision=comparison["head_revision"],
            source_repository=pr["head_repository"],
            report_text=text,
        )
        try:
            analysis_id = service.submit(request)
        except CapacityError as exc:
            raise HTTPException(429, str(exc)) from exc
        store.context(
            analysis_id,
            {
                "pr_number": number,
                "title": pr["title"],
                "url": pr["url"],
                "head_sha": pr["head_sha"],
                "head_repository": pr["head_repository"],
                "base_tip_sha": pr["base_sha"],
                "comparison_basis": comparison["comparison_basis"],
                "files": comparison["files"],
                "diff_note": comparison["diff_note"],
            },
        )
        background.add_task(service.run, analysis_id, text)
        return JSONResponse(
            status_code=202,
            content={"id": analysis_id, "context": comparison},
            headers={"Location": f"/api/analyses/{analysis_id}"},
        )

    @router.get("/repositories/{identifier}/investigations")
    def investigations(identifier: int):
        record = repository(identifier)
        return {"items": store.history(record["url"])}

    @router.get("/investigations")
    def history():
        available()
        return {"items": store.history()}

    return router
