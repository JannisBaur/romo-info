from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Static files the page references by name, bundled as package data and
# copied next to index.html on publish. Kept out of the rendered HTML
# (rather than inlined as data URIs) so ReportFormatter stays pure
# formatting with no file I/O, and so browsers can cache the image
# instead of re-downloading it inside every day's new page.
BUNDLED_ASSETS: tuple[str, ...] = ("dog.jpg",)


class FileReportPublisher:
    """Writes the rendered report and its assets out for a static host.

    The GitHub Pages deploy itself is the workflow's job (see
    .github/workflows/daily-report.yml) -- this only puts the files where
    the workflow expects them, so publishing needs no credentials and no
    network access at all.
    """

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def publish(self, html: str) -> None:
        output_dir = self._output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(html, encoding="utf-8")
        for asset in BUNDLED_ASSETS:
            source = importlib.resources.files("romo_info").joinpath("data", asset)
            (output_dir / asset).write_bytes(source.read_bytes())
        logger.info("Wrote report to %s", self._output_path)
