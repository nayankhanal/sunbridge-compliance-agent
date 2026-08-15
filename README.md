# SunBridge Compliance-Draft Agent (Task 1: China → Nepal)

An autonomous pipeline that fetches two manufacturer datasheets for the same solar
inverter family, reads the **5 kW model's** specs out of each, reconciles the two
sources **field by field**, and produces a clean, source-attributed draft an import
agent can use — showing where the sheets agree, conflict, contradict themselves, or
only mention something once, **without ever picking one value and hiding the other.**

The two source datasheets are different variants (AM2-P1 vs AM2) and different
revisions of the Deye `SUN-...-G06P3` family, so they don't line up cleanly: fields
are named differently, one field is printed twice with different numbers, and the
compliance-standards lists disagree. Surfacing that honestly is the whole point.

---

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Try it with zero setup (fixture data, no key, no network):
python run.py --mock

# Real run — reads the PDFs with a vision model:
cp .env.example .env          # then paste your FREE Gemini key into .env
python run.py

# Tests (reconciliation logic):
pytest -q
```

A **free** Gemini API key (no credit card) comes from
<https://aistudio.google.com/apikey>. The pipeline uses `gemini-flash-latest` (an alias for the current free flash
model), which reads images and returns JSON on the free tier.

Outputs land in `output/`:
- **`reconciled.json`** — structured, machine-readable; every field carries its
  value **per source**, the raw printed text, a **confidence**, and a reconciliation
  **status**.
- **`compliance_draft.md`** — the human-readable draft, grouped by the import
  checklist, conflicts surfaced at the top.

(`output/` is committed so you can read a sample without running anything.)

---

## How it works

A small [LangGraph](https://langchain-ai.github.io/langgraph/) pipeline:

```
fetch  →  render  →  extract (per sheet)  →  reconcile  →  draft
 │          │              │                     │            │
 download   PDF pages      Gemini vision +       compare      Markdown
 both PDFs  → PNG images   schema + retry        field-by-    draft +
 from URLs  (all pages)    → validated JSON      field        JSON
```

Each node is in `src/`; the graph is wired in `src/graph.py`.

### Extraction / OCR approach — and why vision

The Deye spec sheet is a dense multi-column table (8 model columns × ~40 rows).
Plain PDF **text extraction interleaves the columns** — the 5 kW value ends up next
to the wrong model — which is exactly the trap the brief warns about. So instead of
parsing text, the pipeline **renders each page to a 200-DPI image and gives it to a
vision model** (`src/render.py` → `src/extract.py`), which reads the page as laid
out and picks the correct column. Every page is rendered (not a hardcoded "page 2"),
so a re-laid-out revision still works.

### Reliability

- **Schema-constrained output.** The model is bound to a Pydantic schema via
  `.with_structured_output(...)`, so responses are typed, not free text.
- **Validation + retry.** `src/extract.py` validates each response and retries up to
  `MAX_EXTRACT_RETRIES` times; a bad or empty response recovers instead of derailing
  the run.
- **Per-field confidence.** The model marks values `low` when the table layout made a
  column hard to read; those are listed explicitly in the draft.

### Reconciliation (the core)

`src/reconcile.py` compares the two extractions on a **canonical field vocabulary**
(`src/schema.py`, the `FIELDS` registry). Because each sheet labels the same spec
differently ("Max. DC Input Power" vs "Max. PV Input Power"), the model maps its
wording onto stable keys, and reconciliation assigns each field one status:

| Status | Meaning | Example here |
|---|---|---|
| `agree` | both sheets, same value | Rated power = 5 kW |
| `agree_reworded` | same meaning, different words | Transformerless ↔ Non-Isolated |
| `conflict` | both sheets, different values | Max power **5.5 kW** vs **5.5 kVA** |
| `only_one` | present in a single sheet | Overvoltage category (AM2 only) |
| `inconsistent` | a sheet contradicts itself | Weight printed as 4.8 **and** 11 kg |
| `missing` | in neither sheet | — |

Unit differences are treated as conflicts on purpose (`kW ≠ kVA`), and a small
equivalence map handles known synonyms so wording differences aren't reported as
conflicts.

---

## Project structure

```
run.py                     CLI entry point (--mock for a keyless demo)
prompts/extraction_prompt.md   the extraction prompt (a versioned artifact)
src/
  config.py                sources, target model, paths, model settings
  schema.py                Pydantic models + canonical FIELDS registry
  fetch.py                 download PDFs from the public URLs (cached)
  render.py                PDF pages → PNG for the vision model
  llm.py                   model client (swap this one file for another backend)
  extract.py               vision extraction + validation + retry
  reconcile.py             field-by-field comparison → statuses
  draft.py                 renders the Markdown compliance draft
  graph.py                 LangGraph wiring
  fixtures.py              test data for --mock (NOT real output)
tests/test_reconcile.py    unit tests for the reconciliation logic
output/                    sample reconciled.json + compliance_draft.md
```

---

## Assumptions

- SunBridge is ordering the **5 kW model** (`SUN-5K-G06P3`); the full model number's
  variant suffix differs per sheet, so matching is on the stable prefix.
- The two sheets are treated as **different variants/revisions of one product**, so
  cross-sheet differences are reported, not "corrected."
- The import checklist in the brief is used as the field grouping; the *Importer
  paperwork* section is intentionally listed (not silently dropped) even though it
  isn't in a datasheet.
- Values are copied **with units** and never converted or inferred.

## Not hardcoded

No datasheet **value** is written into the code — only which URLs to fetch and which
model row to target. The values are read from the PDFs at run time, so the pipeline
would survive a different revision of the same datasheet. (`src/fixtures.py` contains
hand-written values, but those are **test data** for `--mock`, clearly labeled, and
never used on the real path.)

## Limitations / what I'd do with more time

- **Vision accuracy on tiny cells.** A weaker/free model can still misread a cramped
  number; cropping to the target column before sending would raise confidence.
- **Graph-level retry.** Retry currently lives inside the extract node; a LangGraph
  conditional edge could re-route low-confidence extractions for a second look.
- **Reconciliation is string-based.** Numeric tolerance and unit normalization are
  minimal; a proper units layer would catch more near-matches.
- **One product family.** The canonical field list is tuned to these Deye sheets;
  a new vendor would need its synonyms added.
- **No caching of model responses**, so re-runs re-spend tokens.
- Tests cover reconciliation (pure logic); the vision call is exercised manually.
