"""Reject fixture qualification whose claimed results do not match real artifacts."""

import hashlib
import json

import pytest

from victus.workflows.qualification_records import _fixture_artifacts_match


def _artifact():
    sources = []
    for suffix in ("a", "b"):
        text = f"Real fixture text {suffix}"
        sources.append(
            {
                "url": f"http://127.0.0.1:4567/source-{suffix}.html",
                "text": text,
                "observation_id": f"observation-{suffix}",
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return {
        "kind": "browser_research",
        "status": "succeeded",
        "required_sources": 2,
        "observed_count": 2,
        "sources": sources,
        "summary_is_content_generation": True,
        "environment": {
            "playwright_version": "test-version",
            "explicit_browser_binary": True,
        },
    }


def _write(workspace, artifact, name="sources.json"):
    raw = (json.dumps(artifact) + "\n").encode()
    (workspace / name).write_bytes(raw)
    return {"destination": name, "sha256": hashlib.sha256(raw).hexdigest()}


def test_matching_artifact_is_accepted(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runs = [_write(workspace, _artifact())]
    assert _fixture_artifacts_match(tmp_path / "report.json", runs, "test-version")


def test_report_missing_or_modified_is_rejected(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runs = [_write(workspace, _artifact())]
    (workspace / "sources.json").write_text("{}")
    assert not _fixture_artifacts_match(tmp_path / "report.json", runs, "test-version")
    assert not _fixture_artifacts_match(
        tmp_path / "report.json",
        [{"destination": "../escape.json", "sha256": runs[0]["sha256"]}],
        "test-version",
    )


def test_forged_sources_do_not_qualify_even_with_updated_file_hash(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifact = _artifact()
    artifact["sources"][1]["url"] = artifact["sources"][0]["url"]
    assert not _fixture_artifacts_match(
        tmp_path / "report.json", [_write(workspace, artifact)], "test-version"
    )


def test_wrong_browser_or_source_identity_is_rejected(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifact = _artifact()
    artifact["environment"]["playwright_version"] = "another-version"
    assert not _fixture_artifacts_match(
        tmp_path / "report.json", [_write(workspace, artifact)], "test-version"
    )
    artifact = _artifact()
    artifact["sources"][0]["text_sha256"] = "0" * 64
    assert not _fixture_artifacts_match(
        tmp_path / "report.json", [_write(workspace, artifact)], "test-version"
    )


@pytest.mark.parametrize(
    "change", ["kind", "summary", "environment", "port", "observation", "duplicate_json"]
)
def test_incomplete_or_malformed_artifact_provenance_is_rejected(tmp_path, change):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifact = _artifact()
    if change == "kind":
        artifact["kind"] = "other"
    elif change == "summary":
        artifact.pop("summary_is_content_generation")
    elif change == "environment":
        artifact["environment"]["explicit_browser_binary"] = False
    elif change == "port":
        artifact["sources"][0]["url"] = "http://127.0.0.1/source-a.html"
    elif change == "observation":
        artifact["sources"][0]["observation_id"] = ""
    runs = [_write(workspace, artifact)]
    if change == "duplicate_json":
        path = workspace / "sources.json"
        raw = path.read_text().rstrip()[:-1] + ', "kind": "browser_research"}'
        path.write_text(raw)
        runs[0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not _fixture_artifacts_match(tmp_path / "report.json", runs, "test-version")
