import json

import httpx
import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.github import GitHub, GitHubError
from nobluff.model import OllamaSettings
from nobluff.pipeline import AnalysisService
from nobluff.workspace import Workspace
from test_verification_policy import make_service


def github_client(source_repo):
    original, head = source_repo[1:3]

    def handler(request):
        path = request.url.path
        if path == "/repos/example/fixture":
            data = {
                "full_name": "example/fixture",
                "html_url": "https://github.com/example/fixture",
                "default_branch": "main",
                "private": False,
            }
        elif path.endswith(("/pulls/1", "/pulls")):
            pr = {
                "number": 1,
                "title": "Unicode export raises UnicodeEncodeError",
                "body": "export_csv fails for José.",
                "user": {"login": "contributor"},
                "html_url": "https://github.com/example/fixture/pull/1",
                "state": "open",
                "updated_at": "2026-11-01T00:00:00Z",
                "draft": False,
                "base": {"sha": original, "ref": "main", "repo": {"private": False}},
                "head": {"sha": head, "ref": "unicode-fix"},
            }
            data = [pr] if path.endswith("/pulls") else pr
        elif "/compare/" in path:
            data = {
                "merge_base_commit": {"sha": original},
                "files": [
                    {
                        "filename": "exporter.py",
                        "status": "modified",
                        "patch": "-encoding='ascii'\n+encoding='utf-8'",
                    }
                ],
            }
        else:
            return httpx.Response(404)
        return httpx.Response(200, json=data)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_connect_once_pr_analysis_pins_head_source_and_survives_restart(
    tmp_path, source_repo
):
    db = tmp_path / "workspace.sqlite3"
    store = Workspace(db)
    service, _ = make_service(source_repo, runner=None)
    with (
        github_client(source_repo) as http,
        TestClient(create_app(service, workspace=store, github=GitHub(http))) as client,
    ):
        connected = client.post(
            "/api/repositories", json={"repository": "example/fixture"}
        )
        assert connected.status_code == 201
        rid = connected.json()["id"]
        assert (
            client.post(
                "/api/repositories",
                json={"repository": "https://github.com/example/fixture"},
            ).json()["id"]
            == rid
        )
        assert len(client.get("/api/repositories").json()["items"]) == 1
        pulls = client.get(f"/api/repositories/{rid}/pulls").json()
        assert pulls["items"][0]["number"] == 1
        response = client.post(f"/api/repositories/{rid}/pulls/1/analyses")
        assert response.status_code == 202, response.text
        aid = response.json()["id"]
        report = client.get(f"/api/analyses/{aid}").json()
        assert report["stage"] == "complete", report["errors"]
        assert report["revision"] == source_repo[1]
        assert report["source_revision"] == source_repo[2]
        assert report["comparison_revision"] == source_repo[2]
        assert all(e["revision"] == source_repo[2] for e in report["evidence"])
        history = client.get(f"/api/repositories/{rid}/pulls/1").json()["history"]
        assert history[0]["outdated"] is False
        assert history[0]["context"]["pr_number"] == 1
    restored = Workspace(db)
    fresh = AnalysisService(OllamaSettings(), workspace=restored)
    with TestClient(create_app(fresh, workspace=restored)) as client:
        assert client.get("/api/repositories").json()["items"][0]["id"] == rid
        assert client.get(f"/api/analyses/{aid}").json() == report
        assert client.get(f"/api/analyses/{aid}/export?format=json").json() == report
        assert len(client.get("/api/investigations").json()["items"]) == 1
        assert client.delete(f"/api/repositories/{rid}").status_code == 204
        assert client.get("/api/repositories").json()["items"] == []
        assert client.get(f"/api/analyses/{aid}").status_code == 200


@pytest.mark.parametrize(
    ("status", "expected"), [(404, 404), (403, 429), (429, 429), (301, 502), (500, 502)]
)
def test_github_errors_are_safe_and_actionable(status, expected):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    ) as http:
        with pytest.raises(GitHubError) as error:
            GitHub(http).repository("example/fixture")
        assert error.value.status == expected


def test_default_app_connects_service_to_durable_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("NOBLUFF_DB_PATH", str(tmp_path / "app.sqlite3"))
    with TestClient(create_app()) as client:
        assert client.get("/api/repositories").json() == {"items": []}
    assert (tmp_path / "app.sqlite3").exists()


def test_repository_url_cannot_be_arbitrary_host(tmp_path, source_repo):
    service, _ = make_service(source_repo, None)
    with TestClient(
        create_app(service, workspace=Workspace(tmp_path / "app.sqlite3"))
    ) as client:
        assert (
            client.post(
                "/api/repositories", json={"repository": "https://localhost/private"}
            ).status_code
            == 422
        )
        assert client.get("/api/repositories/999/pulls").status_code == 404
        assert client.get("/api/repositories").json() == {"items": []}


def test_github_response_size_is_bounded():
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=json.dumps({"data": "x" * 2_000_001})
                )
            )
        ) as http,
        pytest.raises(GitHubError, match="limit"),
    ):
        GitHub(http).repository("example/fixture")


def test_fork_source_is_loaded_from_the_head_repository(tmp_path, source_repo):
    from dataclasses import replace

    from nobluff.schemas import AnalysisRequest

    service, original = make_service(source_repo, None)
    calls = []
    original_loader = service.snapshot_loader

    def load(repository, revision):
        calls.append((repository, revision))
        return replace(
            original_loader("https://github.com/example/fixture", revision),
            repository=repository,
        )

    service.snapshot_loader = load
    request = AnalysisRequest(
        repository="https://github.com/example/fixture",
        revision=original,
        source_repository="https://github.com/contributor/fixture",
        source_revision=source_repo[2],
        comparison_revision=source_repo[2],
        report_text="export_csv fails",
    )
    identifier = service.submit(request)
    service.run(identifier, request.report_text)
    report = service.get(identifier)
    assert report.stage == "complete"
    assert report.source_repository == "https://github.com/contributor/fixture"
    assert calls == [
        ("https://github.com/example/fixture", original),
        ("https://github.com/contributor/fixture", source_repo[2]),
    ]


def test_running_report_is_marked_interrupted_after_restart(tmp_path):
    from nobluff.schemas import AnalysisRequest

    store = Workspace(tmp_path / "workspace.sqlite3")
    first = AnalysisService(OllamaSettings(), workspace=store)
    identifier = first.submit(
        AnalysisRequest(
            repository="https://github.com/example/fixture",
            revision="main",
            report_text="claim",
        )
    )
    restarted = AnalysisService(OllamaSettings(), workspace=store)
    report = restarted.get(identifier)
    assert report.stage == "error"
    assert "interrupted" in report.errors[0]


def test_twenty_repository_limit_returns_409_and_reconnecting_returns_201(tmp_path):
    def handler(request):
        if request.url.path.startswith("/repos/"):
            name = request.url.path.removeprefix("/repos/")
            return httpx.Response(
                200,
                json={
                    "full_name": name,
                    "html_url": f"https://github.com/{name}",
                    "default_branch": "main",
                    "private": False,
                },
            )
        return httpx.Response(404)

    store = Workspace(tmp_path / "workspace.sqlite3")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http,
        TestClient(create_app(workspace=store, github=GitHub(http))) as client,
    ):
        for i in range(20):
            response = client.post(
                "/api/repositories", json={"repository": f"example/repo-{i}"}
            )
            assert response.status_code == 201

        over_limit = client.post(
            "/api/repositories", json={"repository": "example/repo-20"}
        )
        assert over_limit.status_code == 409
        assert (
            over_limit.json()["detail"]
            == "Disconnect a repository before adding more than 20."
        )

        reconnect = client.post(
            "/api/repositories", json={"repository": "example/repo-0"}
        )
        assert reconnect.status_code == 201

