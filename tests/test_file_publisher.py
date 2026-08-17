from __future__ import annotations

from pathlib import Path

from romo_info.clients.file_publisher import BUNDLED_ASSETS, FileReportPublisher


def test_publish_writes_the_html_to_the_configured_path(tmp_path: Path) -> None:
    output = tmp_path / "index.html"

    FileReportPublisher(output).publish("<!doctype html><p>hi</p>")

    assert output.read_text(encoding="utf-8") == "<!doctype html><p>hi</p>"


def test_publish_creates_missing_parent_directories(tmp_path: Path) -> None:
    output = tmp_path / "public" / "nested" / "index.html"

    FileReportPublisher(output).publish("<p>hi</p>")

    assert output.exists()


def test_publish_overwrites_a_previous_report(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    publisher = FileReportPublisher(output)

    publisher.publish("<p>yesterday</p>")
    publisher.publish("<p>today</p>")

    assert output.read_text(encoding="utf-8") == "<p>today</p>"


def test_publish_copies_bundled_assets_next_to_the_page(tmp_path: Path) -> None:
    # The page references these by relative name, so they have to land in
    # the same directory as index.html or the deployed site 404s on them.
    output = tmp_path / "public" / "index.html"

    FileReportPublisher(output).publish("<p>hi</p>")

    for asset in BUNDLED_ASSETS:
        copied = output.parent / asset
        assert copied.exists(), f"{asset} was not copied"
        assert copied.stat().st_size > 0


def test_publish_assets_survive_a_republish(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    publisher = FileReportPublisher(output)

    publisher.publish("<p>yesterday</p>")
    publisher.publish("<p>today</p>")

    assert all((output.parent / asset).exists() for asset in BUNDLED_ASSETS)
