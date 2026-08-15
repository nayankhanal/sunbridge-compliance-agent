"""LangGraph pipeline: fetch -> render -> extract -> reconcile -> draft.

A deliberately small, linear graph. State is a plain dict; each node returns the
keys it updates. Retry/validation lives inside the extract node (see extract.py)
so a flaky model response recovers instead of derailing the whole run.

`mock=True` skips fetch/render/extract-via-API and injects fixture extractions,
so the graph runs end to end with no key and no network (used by tests and demos).
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .config import SOURCES
from .draft import render_markdown
from .extract import extract_datasheet
from .fetch import fetch_pdf
from .reconcile import reconcile
from .render import render_pdf_to_images
from .schema import DatasheetExtraction, ReconciliationResult


class PipelineState(TypedDict, total=False):
    mock: bool
    log: list[str]
    pdf_paths: dict
    image_paths: dict
    extractions: list[DatasheetExtraction]
    result: ReconciliationResult
    draft_md: str


def fetch_node(state: PipelineState) -> dict:
    log = state.get("log", [])
    if state.get("mock"):
        log.append("[fetch] mock mode — skipped")
        return {"log": log}
    paths = {}
    for s in SOURCES:
        paths[s.id] = fetch_pdf(s)
        log.append(f"[fetch] {s.id} -> {paths[s.id].name}")
    return {"pdf_paths": paths, "log": log}


def render_node(state: PipelineState) -> dict:
    log = state.get("log", [])
    if state.get("mock"):
        log.append("[render] mock mode — skipped")
        return {"log": log}
    images = {}
    for s in SOURCES:
        imgs = render_pdf_to_images(state["pdf_paths"][s.id])
        images[s.id] = imgs
        log.append(f"[render] {s.id} -> {len(imgs)} page image(s)")
    return {"image_paths": images, "log": log}


def extract_node(state: PipelineState) -> dict:
    log = state.get("log", [])
    if state.get("mock"):
        from .fixtures import mock_extractions
        ex = mock_extractions()
        log.append(f"[extract] mock fixtures loaded ({len(ex)} sheets)")
        return {"extractions": ex, "log": log}
    ex = [extract_datasheet(s, state["image_paths"][s.id], log) for s in SOURCES]
    return {"extractions": ex, "log": log}


def reconcile_node(state: PipelineState) -> dict:
    log = state.get("log", [])
    result = reconcile(state["extractions"])
    log.append(f"[reconcile] compared {len(result.fields)} fields")
    return {"result": result, "log": log}


def draft_node(state: PipelineState) -> dict:
    log = state.get("log", [])
    md = render_markdown(state["result"])
    log.append(f"[draft] rendered {len(md)} chars")
    return {"draft_md": md, "log": log}


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("fetch", fetch_node)
    g.add_node("render", render_node)
    g.add_node("extract", extract_node)
    g.add_node("reconcile", reconcile_node)
    g.add_node("draft", draft_node)
    g.add_edge(START, "fetch")
    g.add_edge("fetch", "render")
    g.add_edge("render", "extract")
    g.add_edge("extract", "reconcile")
    g.add_edge("reconcile", "draft")
    g.add_edge("draft", END)
    return g.compile()
