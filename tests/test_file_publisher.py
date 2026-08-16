from __future__ import annotations

from pathlib import Path

from romo_bot.clients.file_publisher import FileReportPublisher


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
