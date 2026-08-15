"""Compare the two per-sheet extractions field by field.

This is where "show both sides honestly" happens. For every canonical field we
decide one of:
    agree           both sources, same value
    agree_reworded  same meaning, different words (Transformerless == Non-Isolated)
    conflict        both sources, genuinely different values (5.5 kW vs 5.5 kVA)
    only_one        present in a single sheet
    inconsistent    a sheet contradicts itself (weight printed as 4.8 and 11 kg)
    missing         in neither sheet

We never drop a value or pick a winner -- both are always carried into the output.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .config import SOURCES, TARGET_MODEL_PREFIX, TARGET_POWER
from .schema import (
    Confidence,
    DatasheetExtraction,
    FIELDS,
    ReconciledField,
    ReconciliationResult,
    ReconStatus,
    SourceMeta,
)

# Values that read differently but mean the same thing.
EQUIVALENCE_GROUPS: list[set[str]] = [
    {"transformerless", "non-isolated", "non isolated", "transformer-less"},
    {"free cooling", "natural cooling", "natural convection"},
]

# Words in a per-field note that signal a self-contradiction on one sheet.
INCONSISTENT_HINTS = (
    "inconsist", "twice", "two values", "two different", "contradict",
    "duplicat", "conflicting",
)


def _norm(v: str | None) -> str | None:
    """Normalize formatting so cosmetic differences don't read as conflicts.

    Only whitespace/punctuation spacing is unified -- content is left intact, so
    genuine differences (e.g. one sheet listing more standards) still surface.
    """
    if v is None:
        return None
    s = v.strip().lower().replace("℃", "°c")
    s = re.sub(r"\s*%\s*", "%", s)     # "98.3 %"  -> "98.3%"
    s = re.sub(r"\s*/\s*", "/", s)      # "2 / 1+1" -> "2/1+1"
    s = re.sub(r"\s*,\s*", ",", s)      # "a, b"    -> "a,b"
    s = re.sub(r"\s*(°)", r"\1", s)     # "+60 °c"  -> "+60°c"
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(". ")


def _same_group(a: str | None, b: str | None) -> bool:
    return any(a in g and b in g for g in EQUIVALENCE_GROUPS)


def _unit_of(v: str | None) -> str:
    tokens = re.findall(r"[a-zA-Z%°]+", v or "")
    return tokens[-1].lower() if tokens else ""


def _units_differ(a: str | None, b: str | None) -> bool:
    return _unit_of(a) != _unit_of(b)


def _looks_inconsistent(note: str | None) -> bool:
    return bool(note) and any(h in note.lower() for h in INCONSISTENT_HINTS)


def reconcile(extractions: list[DatasheetExtraction]) -> ReconciliationResult:
    by_source = {e.source_id: e for e in extractions}
    # keep the order defined in config
    source_ids = [s.id for s in SOURCES if s.id in by_source]

    # index: source_id -> {field key -> ExtractedField}
    field_index = {
        e.source_id: {f.key: f for f in e.fields} for e in extractions
    }

    recon_fields: list[ReconciledField] = []
    for spec in FIELDS:
        key = spec.key
        vals: dict[str, str | None] = {}
        raws: dict[str, str | None] = {}
        confs: dict[str, Confidence] = {}
        present_sources: list[str] = []
        inconsistent_flag = False
        per_source_notes: list[str] = []

        for sid in source_ids:
            f = field_index.get(sid, {}).get(key)
            has_value = f is not None and f.present and f.value not in (None, "")
            vals[sid] = f.value if has_value else None
            raws[sid] = f.raw_text if f else None
            confs[sid] = f.confidence if f else Confidence.low
            if has_value:
                present_sources.append(sid)
            if f and f.note:
                per_source_notes.append(f"{sid}: {f.note}")
                if _looks_inconsistent(f.note):
                    inconsistent_flag = True

        note: str | None = None
        if len(present_sources) == 0:
            status = ReconStatus.missing
        elif len(present_sources) == 1:
            status = ReconStatus.only_one
            note = f"Only stated in {present_sources[0]}."
        else:
            a, b = present_sources[0], present_sources[1]
            na, nb = _norm(vals[a]), _norm(vals[b])
            if na == nb:
                status = ReconStatus.agree
            elif _same_group(na, nb):
                status = ReconStatus.agree_reworded
                note = "Same meaning, different wording."
            else:
                status = ReconStatus.conflict
                if spec.unit_sensitive and _units_differ(vals[a], vals[b]):
                    note = ("Values differ in unit/quantity (e.g. kW vs kVA) -- "
                            "confirm which the factory means.")
                else:
                    note = "Sources give different values."

        if inconsistent_flag and status in (
            ReconStatus.agree, ReconStatus.agree_reworded, ReconStatus.only_one
        ):
            status = ReconStatus.inconsistent

        parts = [p for p in [note] if p]
        if inconsistent_flag:
            parts.append("A source's value looks internally inconsistent.")
        parts.extend(per_source_notes)
        note = " ".join(parts) if parts else None

        recon_fields.append(ReconciledField(
            key=key, label=spec.label, category=spec.category,
            status=status, values=vals, raw=raws, confidence=confs, note=note,
        ))

    sources_meta = [
        SourceMeta(
            id=s.id, url=s.url, variant_expected=s.variant,
            variant_detected=by_source[s.id].variant_detected, revision_hint=s.revision,
        )
        for s in SOURCES if s.id in by_source
    ]

    variants = ", ".join(
        f"{e.source_id}={e.variant_detected or '?'}" for e in extractions
    )
    notes = [
        f"The two sheets describe different variants of the same 5 kW model "
        f"({variants}). Cross-sheet differences are expected variant/revision "
        f"differences, not necessarily errors.",
    ]

    return ReconciliationResult(
        target_model=f"{TARGET_MODEL_PREFIX} ({TARGET_POWER})",
        target_power=TARGET_POWER,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sources=sources_meta,
        fields=recon_fields,
        notes=notes,
    )
