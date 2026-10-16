"""Real filesystem tests for destination/file-bound permits and staging."""

from dataclasses import replace

import pytest

from victus.adapters.playwright.downloads import DownloadStaging, TransferBlocked
from victus.adapters.playwright.uploads import UploadReviews


@pytest.fixture
def staging(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    return DownloadStaging(tmp_path, "task", destination_roots=(output,)), output


def test_release_requires_explicit_receipt_and_destination_and_never_overwrites(staging):
    manager, output = staging
    receipt = manager.stage_bytes(b"content")
    assert not list(output.iterdir())
    with pytest.raises(TransferBlocked):
        manager.release(receipt.download_id)
    permit = manager.approve_release(receipt, output / "note.txt")
    assert manager.release(permit).read_bytes() == b"content"
    with pytest.raises(TransferBlocked):
        manager.release(permit)
    other = manager.stage_bytes(b"replacement")
    with pytest.raises(TransferBlocked, match="EXISTS"):
        manager.approve_release(other, output / "note.txt")
    assert (output / "note.txt").read_bytes() == b"content"


@pytest.mark.parametrize(
    "name",
    [
        "../escape.txt",
        "x:y.txt",
        "CON.txt",
        "trailing.",
        "trailing ",
        "a\\b",
        "CONIN$",
        "COM¹.txt",
        "NUL .txt",
    ],
)
def test_unsafe_download_destinations(staging, name):
    manager, output = staging
    receipt = manager.stage_bytes(b"data")
    with pytest.raises(TransferBlocked):
        manager.approve_release(receipt, output / name)


def test_staged_file_tampering_and_forged_receipts_are_blocked(staging):
    manager, output = staging
    receipt = manager.stage_bytes(b"original")
    with pytest.raises(TransferBlocked):
        manager.approve_release(replace(receipt, sha256="fake"), output / "note")
    permit = manager.approve_release(receipt, output / "note")
    (manager._root / receipt.download_id).write_bytes(b"tampered")
    with pytest.raises(TransferBlocked, match="CHANGED"):
        manager.release(permit)
    assert not (output / "note").exists()


def test_staging_limits_and_discard(staging):
    manager, _ = staging
    manager._max_bytes = 2
    with pytest.raises(TransferBlocked, match="LIMIT"):
        manager.stage_bytes(b"too large")
    receipt = manager.stage_bytes(b"ok")
    manager.discard(receipt)
    assert not list(manager._root.iterdir())


def test_upload_review_binds_exact_files_and_destination(tmp_path):
    path = tmp_path / "report.txt"
    path.write_bytes(b"report")
    reviews = UploadReviews("task", source_roots=(tmp_path,))
    review = reviews.review((path,), "https://example.test/upload")
    with pytest.raises(TransferBlocked):
        reviews._consume(review.review_id, review.destination)
    permit = reviews.approve(review)
    payloads = reviews._consume(permit, review.destination)
    assert payloads[0]["buffer"] == b"report"
    with pytest.raises(TransferBlocked):
        reviews._consume(permit, review.destination)


def test_changed_upload_file_and_destination_blocked(tmp_path):
    path = tmp_path / "report.txt"
    path.write_bytes(b"report")
    reviews = UploadReviews("task", source_roots=(tmp_path,))
    review = reviews.review((path,), "https://example.test/upload")
    permit = reviews.approve(review)
    with pytest.raises(TransferBlocked, match="DESTINATION"):
        reviews._consume(permit, "https://elsewhere.test/")
    permit = reviews.approve(review)
    path.write_bytes(b"changed")
    with pytest.raises(TransferBlocked, match="CHANGED"):
        reviews._consume(permit, review.destination)


def test_upload_requires_concrete_regular_files_not_directories(tmp_path):
    reviews = UploadReviews("task", source_roots=(tmp_path,))
    with pytest.raises(TransferBlocked):
        reviews.review((), "https://example.test/upload")
    with pytest.raises((TransferBlocked, OSError)):
        reviews.review((tmp_path,), "https://example.test/upload")


def test_upload_preparation_uses_reviewed_bytes_not_arbitrary_paths(tmp_path):
    import asyncio
    from unittest.mock import AsyncMock, Mock

    async def run():
        path = tmp_path / "reviewed.txt"
        path.write_bytes(b"exact reviewed contents")
        reviews = UploadReviews("task", source_roots=(tmp_path,))
        destination = "https://example.test/upload"
        permit = reviews.approve(reviews.review((path,), destination))
        target = Mock()
        target.binding.identity = {"tag": "input", "type": "file"}
        target.element.evaluate = AsyncMock(return_value=destination)
        target.element.set_input_files = AsyncMock()
        target.element.dispose = AsyncMock()
        resolver = Mock(
            _network_task_id="task", _upload_reviews=reviews, _operation_lock=asyncio.Lock()
        )
        resolver.resolve_target = AsyncMock(return_value=target)
        resolver._assert_fresh = AsyncMock()
        await reviews.prepare_input(resolver, "target-ref", "observation", permit, destination)
        payloads = target.element.set_input_files.call_args.args[0]
        assert payloads[0]["buffer"] == b"exact reviewed contents"
        assert payloads[0]["name"] == "reviewed.txt"
        assert "path" not in payloads[0]
        target.element.dispose.assert_awaited_once()
        resolver.invalidate.assert_called_once_with("observation")

    asyncio.run(run())


def test_expired_release_cannot_move_file(staging):
    manager, output = staging
    receipt = manager.stage_bytes(b"data")
    permit = manager.approve_release(receipt, output / "note")
    manager._permits[permit] = (receipt, output / "note", 0)
    with pytest.raises(TransferBlocked, match="INVALID"):
        manager.release(permit)
    assert not (output / "note").exists()
    assert (manager._root / receipt.download_id).exists()
