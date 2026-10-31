import io
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.model import AssessmentResult, ClaimExtractionResult, OllamaSettings
from nobluff.pipeline import AnalysisService
from nobluff.repositories import RepositoryLoader
from nobluff.retrieval import SnapshotError
from nobluff.schemas import Claim, Finding


def test_full_source_pipeline_pins_and_assesses(source_repo):
    repo, original, _, _ = source_repo
    loader = RepositoryLoader({"https://github.com/example/fixture": str(repo)})

    def extract(text, settings):
        return ClaimExtractionResult(
            model=settings.model,
            created_at="fixture",
            attempts=1,
            elapsed_ms=1,
            claims=[
                Claim(
                    id="c1",
                    text="ASCII is selected.",
                    kind="behavior",
                    search_terms=["encoding"],
                )
            ],
        )

    def assess(claims, evidence, settings):
        assert evidence and all(e.revision == original for e in evidence)
        assert any("'ascii'" in e.excerpt for e in evidence)
        return AssessmentResult(
            model=settings.model,
            basis="qwen",
            created_at="fixture",
            attempts=1,
            elapsed_ms=1,
            findings=[
                Finding(
                    claim_id="c1",
                    assessment="supported",
                    evidence_ids=[evidence[0].id],
                    explanation="Source selects ASCII.",
                    limitations=["Static review only."],
                )
            ],
        )

    service = AnalysisService(
        OllamaSettings(),
        extractor=extract,
        assessor=assess,
        snapshot_loader=loader.load,
    )
    with TestClient(create_app(service)) as client:
        response = client.post(
            "/api/analyses",
            json={
                "repository": "example/fixture",
                "revision": original,
                "report_text": "ASCII is selected.",
            },
        )
        report = client.get(response.headers["location"]).json()
        assert report["stage"] == "complete"
        assert report["revision"] == original
        assert report["findings"][0]["assessment"] == "supported"
        assert report["executions"] == []
        assert (
            client.get(response.headers["location"] + "/export?format=json").json()
            == report
        )


def archive(name, commit, members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        for path, text in members.items():
            z.writestr(f"{name}-{commit}/{path}", text)
    return output.getvalue()


def test_public_loader_resolves_before_download(tmp_path):
    sha = "a" * 40
    urls = []

    def handler(request):
        urls.append(str(request.url))
        if request.url.host == "api.github.com":
            return httpx.Response(200, json={"sha": sha})
        return httpx.Response(
            200, content=archive("repo", sha, {"x.py": "value = 1\n"})
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        loader = RepositoryLoader(client=client)
        snapshot = loader.load("https://github.com/owner/repo", "main")
        assert snapshot.commit == sha
        assert snapshot.get("x.py").text == "value = 1\n"
        assert urls[-1].endswith("/" + sha)
        location = snapshot.location
        loader.close()
        assert not location.exists()


@pytest.mark.parametrize(
    "path", ["../escape.py", "/etc/a.py", "nested/../../escape.py", "x\\y.py"]
)
def test_archive_traversal_rejected(path):
    sha = "a" * 40

    def handler(request):
        return (
            httpx.Response(200, json={"sha": sha})
            if request.url.host == "api.github.com"
            else httpx.Response(200, content=archive("repo", sha, {path: "x"}))
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        loader = RepositoryLoader(client=client)
        with pytest.raises(SnapshotError):
            loader.load("https://github.com/owner/repo", "main")
        loader.close()


@pytest.mark.parametrize("status", [302, 403, 404, 429])
def test_github_errors_not_silently_followed(status):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(status))
        ) as client,
        pytest.raises(SnapshotError),
    ):
        RepositoryLoader(client=client).load("https://github.com/owner/repo", "main")


def test_failed_loading_does_not_produce_verdict():
    def fail(repo, revision):
        raise SnapshotError("Pinned source unavailable")

    service = AnalysisService(OllamaSettings(), snapshot_loader=fail)
    with TestClient(create_app(service)) as client:
        response = client.post(
            "/api/analyses",
            json={"repository": "owner/repo", "revision": "main", "report_text": "x"},
        )
        report = client.get(response.headers["location"]).json()
        assert report["stage"] == "error"
        assert report["findings"] == []


def test_invalid_assessment_fails_closed_without_blocking_reviewed_verification(
    source_repo,
):
    from nobluff.model import ExtractionError
    from test_verification_policy import make_service

    service, original = make_service(source_repo, runner=None)

    def rejected(*args):
        raise ExtractionError("invalid_output", "Rejected structured response")

    service.assessor = rejected
    with TestClient(create_app(service)) as client:
        identifier = client.post(
            "/api/analyses",
            json={
                "repository": "example/fixture",
                "revision": original,
                "report_text": "unicode fails",
            },
        ).json()["id"]
        report = client.get(f"/api/analyses/{identifier}").json()
        assert report["stage"] == "complete"
        assert report["findings"][0]["assessment"] == "inconclusive"
        assert report["findings"][0]["evidence_ids"] == []
        assert "rejected" in report["warnings"][0]
        assert report["executions"] == []
