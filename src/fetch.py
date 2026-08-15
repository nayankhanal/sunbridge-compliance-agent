"""Download the source datasheets from their public URLs.

Fetching is deliberately part of the pipeline (not pre-downloaded) so the run is
reproducible from the links alone. Files are cached under data/ to avoid
re-downloading on every run.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from .config import DATA_DIR, Source

# Some CDNs reject the default httpx user-agent; use a browser-like one.
USER_AGENT = "Mozilla/5.0 (compatible; SunBridgeComplianceBot/1.0; +local-pipeline)"


def fetch_pdf(source: Source, force: bool = False) -> Path:
    """Download one datasheet, cache it, and return the local path."""
    dest = DATA_DIR / f"{source.id}.pdf"
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest

    with httpx.Client(follow_redirects=True, timeout=30.0,
                      headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(source.url)
        resp.raise_for_status()
        data = resp.content

    if data[:4] != b"%PDF":
        raise ValueError(
            f"{source.url} did not return a PDF (first bytes: {data[:16]!r}). "
            "The link may have moved."
        )

    dest.write_bytes(data)
    return dest
