"""CLI entry point.

    python run.py          # real run, needs GOOGLE_API_KEY in .env
    python run.py --mock   # fixture run, no key or network

Writes output/reconciled.json and output/compliance_draft.md.
"""
from __future__ import annotations

import argparse
import json

from src.config import OUTPUT_DIR
from src.graph import build_graph


def main() -> None:
    ap = argparse.ArgumentParser(description="SunBridge compliance draft pipeline (Task 1)")
    ap.add_argument("--mock", action="store_true",
                    help="run with fixture extractions (no API key or network)")
    args = ap.parse_args()

    app = build_graph()
    final = app.invoke({"mock": args.mock, "log": []})

    result = final["result"]
    json_path = OUTPUT_DIR / "reconciled.json"
    md_path = OUTPUT_DIR / "compliance_draft.md"
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(final["draft_md"], encoding="utf-8")

    print("\n".join(final["log"]))
    print(f"\nWrote:\n  {json_path}\n  {md_path}")


if __name__ == "__main__":
    main()
