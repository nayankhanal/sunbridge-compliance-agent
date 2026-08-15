"""Model client factory.

Isolated here so the rest of the pipeline never imports a provider directly --
swap this one file to run on a different backend (e.g. a local Ollama vision
model) without touching the graph.
"""
from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from .config import GEMINI_MODEL, require_api_key


def get_vision_model(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Gemini multimodal model. temperature=0 for deterministic extraction."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=require_api_key(),
        temperature=temperature,
    )
