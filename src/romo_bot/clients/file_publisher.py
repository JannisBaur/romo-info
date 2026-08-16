from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileReportPublisher:
    """Writes the rendered report to a file for a static host to serve.

    The GitHub Pages deploy itself is the workflow's job (see
    .github/workflows/daily-report.yml) -- this only puts the file where
    the workflow expects it, so publishing needs no credentials and no
    network access at all.
    """

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def publish(self, html: str) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(html, encoding="utf-8")
        logger.info("Wrote report to %s", self._output_path)
