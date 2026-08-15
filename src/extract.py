"""Vision extraction for one datasheet: schema-constrained output, validated,
with a bounded retry so a bad response doesn't kill the run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from .config import MAX_EXTRACT_RETRIES, PROMPTS_DIR, TARGET_DESCRIPTION, Source
from .llm import get_vision_model
from .render import image_to_data_uri
from .schema import FIELD_KEYS, FIELDS, DatasheetExtraction


def _build_prompt() -> str:
    template = (PROMPTS_DIR / "extraction_prompt.md").read_text()
    field_lines = "\n".join(
        f"- {f.key} -- {f.label}"
        + (f"; seen as: {', '.join(f.synonyms)}" if f.synonyms else "")
        for f in FIELDS
    )
    return template.format(target_description=TARGET_DESCRIPTION, field_list=field_lines)


def _build_message(image_paths: list[Path]) -> HumanMessage:
    content: list[dict] = [{"type": "text", "text": _build_prompt()}]
    for img in image_paths:
        # LangChain multimodal standard: image_url as {"url": <data-uri>}.
        content.append(
            {"type": "image_url", "image_url": {"url": image_to_data_uri(img)}}
        )
    return HumanMessage(content=content)


def extract_datasheet(
    source: Source,
    image_paths: list[Path],
    log: Optional[list[str]] = None,
) -> DatasheetExtraction:
    """Run the vision model against one datasheet's page images."""
    structured = get_vision_model().with_structured_output(DatasheetExtraction)
    message = _build_message(image_paths)

    last_err: Optional[Exception] = None
    for attempt in range(1, MAX_EXTRACT_RETRIES + 1):
        try:
            result: DatasheetExtraction = structured.invoke([message])
            result.source_id = source.id
            result.source_url = source.url
            # Guard against invented keys: keep only known ones.
            result.fields = [f for f in result.fields if f.key in FIELD_KEYS]
            if not result.fields:
                raise ValueError("model returned no recognized fields")
            if log is not None:
                log.append(
                    f"[extract:{source.id}] ok on attempt {attempt} "
                    f"({len(result.fields)} fields)"
                )
            return result
        except (ValidationError, ValueError, Exception) as e:  # noqa: BLE001
            last_err = e
            if log is not None:
                log.append(f"[extract:{source.id}] attempt {attempt} failed: {e!r}")

    raise RuntimeError(
        f"extraction failed for {source.id} after {MAX_EXTRACT_RETRIES} attempts: {last_err}"
    )
