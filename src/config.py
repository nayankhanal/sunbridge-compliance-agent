"""Config - source URLs, target model, paths, model settings.

Only the URLs and the target model row live here; no spec values are hardcoded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# --- Paths ----------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")  # load from the project root, regardless of cwd
DATA_DIR = ROOT_DIR / "data"       # downloaded PDFs + rendered page images (regenerated)
OUTPUT_DIR = ROOT_DIR / "output"   # reconciled.json + compliance_draft.md
PROMPTS_DIR = ROOT_DIR / "prompts"

for _d in (DATA_DIR, OUTPUT_DIR):
    _d.mkdir(exist_ok=True)


# --- Source documents (Task 1) --------------------------------------------
@dataclass(frozen=True)
class Source:
    id: str            # short label used for attribution in every output
    variant: str       # variant we expect (verified against the sheet at run time)
    revision: str      # revision hint from the file name (not authoritative)
    url: str


SOURCES: list[Source] = [
    Source(
        id="AM2-P1",
        variant="AM2-P1",
        revision="2023-10-07",
        url="https://www.deyeinverter.com/deyeinverter/2023/10/07/"
            "datasheet_sun-4-12k-g06p3-eu-am2-p1_231007_en.pdf",
    ),
    Source(
        id="AM2",
        variant="AM2",
        revision="2024-03-18",
        url="https://www.deyeinverter.com/deyeinverter/2024/03/20/"
            "datasheet_sun-4-15k-g06p3-eu-am2_240318_en.pdf",
    ),
]


# 5 kW model. The variant suffix differs between sheets, so match on the prefix.
TARGET_MODEL_PREFIX = "SUN-5K-G06P3"
TARGET_POWER = "5 kW"
TARGET_DESCRIPTION = (
    "the 5 kW model, whose model number starts with 'SUN-5K-G06P3' "
    "(the full number ends in a variant suffix such as -EU-AM2-P1 or -EU-AM2)"
)


# gemini-flash-latest is an alias for the current free flash model, so this
# keeps working when Google renames versions.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

RENDER_DPI = int(os.getenv("RENDER_DPI", "200"))   # page image resolution for vision
MAX_EXTRACT_RETRIES = int(os.getenv("MAX_EXTRACT_RETRIES", "3"))


def require_api_key() -> str:
    """Fail early with a helpful message if the key is missing."""
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/apikey and put it in a .env file "
            "(see .env.example). Or run with --mock to try the pipeline "
            "without a key."
        )
    return GOOGLE_API_KEY
