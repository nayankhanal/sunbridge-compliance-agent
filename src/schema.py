"""Data model for the pipeline.

Two layers:
  1. What one datasheet says   -> DatasheetExtraction (list of ExtractedField)
  2. What the two sheets say together -> ReconciliationResult (list of ReconciledField)

The FIELDS registry is the canonical vocabulary. Each datasheet labels the same
spec differently ("Max. DC Input Power" vs "Max. PV Input Power"), so we ask the
vision model to map whatever it sees onto these stable keys, and record the
original wording in `raw_text` for traceability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------
class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Category(str, Enum):
    product_identity = "product_identity"
    manufacturer_identity = "manufacturer_identity"
    test_evidence = "test_evidence"
    labeling = "labeling"


class ReconStatus(str, Enum):
    agree = "agree"                    # both sources, same value
    agree_reworded = "agree_reworded"  # same meaning, different wording
    conflict = "conflict"              # both sources, genuinely different values
    only_one = "only_one"              # present in a single source
    inconsistent = "inconsistent"      # one source contradicts itself
    missing = "missing"                # in neither source


# --------------------------------------------------------------------------
# Canonical field registry
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str                 # human label for the draft
    category: Category
    synonyms: tuple[str, ...] = field(default_factory=tuple)  # labels seen on sheets
    unit_sensitive: bool = False  # if True, a unit difference (kW vs kVA) is a conflict


CATEGORY_TITLES = {
    Category.product_identity: "1. Product identity",
    Category.manufacturer_identity: "2. Manufacturer identity",
    Category.test_evidence: "3. Test evidence & standards",
    Category.labeling: "4. Labeling",
}

FIELDS: list[FieldSpec] = [
    # --- Product identity ---
    FieldSpec("model_number", "Model number (5 kW)", Category.product_identity,
              ("Model",)),
    FieldSpec("rated_output_power", "Rated output power", Category.product_identity,
              ("Rated Output Power", "Rated AC Output Active Power"), unit_sensitive=True),
    FieldSpec("max_power", "Max. output power", Category.product_identity,
              ("Max. Active Power", "Max. AC Output Apparent Power"), unit_sensitive=True),
    FieldSpec("rated_ac_output_current", "Rated AC output current", Category.product_identity,
              ("Rated AC Grid Output Current", "Rated AC Output Current")),
    FieldSpec("max_ac_output_current", "Max. AC output current", Category.product_identity,
              ("Max. AC Output Current",)),
    FieldSpec("output_voltage_range", "Output voltage / range", Category.product_identity,
              ("Rated Output Voltage/Range",)),
    FieldSpec("grid_frequency", "Grid frequency", Category.product_identity,
              ("Rated Grid Frequency", "Rated Output Grid Frequency/Range")),
    FieldSpec("phase", "Operating phase / grid form", Category.product_identity,
              ("Operating Phase", "Grid Connection Form")),
    FieldSpec("mppt_trackers_strings", "MPP trackers / strings", Category.product_identity,
              ("No.of MPP Trackers", "No. of MPP Trackers/ No. of Strings per MPP Tracker")),
    FieldSpec("max_efficiency", "Max. efficiency", Category.product_identity,
              ("Max. Efficiency",)),
    FieldSpec("euro_efficiency", "Euro efficiency", Category.product_identity,
              ("Euro Efficiency",)),
    FieldSpec("topology", "Topology", Category.product_identity,
              ("Topology",)),
    FieldSpec("max_dc_input_power", "Max. DC/PV input power", Category.product_identity,
              ("Max. DC Input Power", "Max. PV Input Power")),
    FieldSpec("mppt_voltage_range", "MPPT voltage range", Category.product_identity,
              ("MPPT Operating Range", "MPPT Voltage Range")),

    # --- Manufacturer identity ---
    FieldSpec("manufacturer_name", "Manufacturer (legal name)", Category.manufacturer_identity,
              ("Ningbo Deye Inverter Technology",)),
    FieldSpec("manufacturer_address", "Factory address", Category.manufacturer_identity,
              ("Add",)),
    FieldSpec("country_of_manufacture", "Country of manufacture", Category.manufacturer_identity),

    # --- Test evidence & standards ---
    FieldSpec("grid_connection_standards", "Grid-connection standards", Category.test_evidence,
              ("Grid Connection Standard", "Grid Regulation")),
    FieldSpec("safety_emc_standards", "Safety / EMC standards", Category.test_evidence,
              ("Safety / EMC Standard", "Safety EMC/Standard")),
    FieldSpec("overvoltage_category", "Overvoltage category", Category.test_evidence,
              ("Over Voltage Category",)),
    FieldSpec("warranty", "Warranty", Category.test_evidence,
              ("Warranty",)),

    # --- Labeling ---
    FieldSpec("ip_rating", "Ingress protection (IP) rating", Category.labeling,
              ("Ingress Protection", "Ingress Protection(IP) Rating")),
    FieldSpec("weight", "Weight", Category.labeling,
              ("Weight",)),
    FieldSpec("dimensions", "Dimensions (WxHxD)", Category.labeling,
              ("Cabinet Size",)),
    FieldSpec("operating_temp_range", "Operating temperature range", Category.labeling,
              ("Running Temperature", "Operating Temperature Range")),
    FieldSpec("cooling", "Cooling method", Category.labeling,
              ("Cooling Concept", "Type of Cooling")),
]

FIELDS_BY_KEY: dict[str, FieldSpec] = {f.key: f for f in FIELDS}
FIELD_KEYS: set[str] = set(FIELDS_BY_KEY)


# --------------------------------------------------------------------------
# Layer 1 -- one datasheet
# --------------------------------------------------------------------------
class ExtractedField(BaseModel):
    key: str = Field(description="canonical field key from the allowed list")
    value: Optional[str] = Field(
        default=None,
        description="value for the 5 kW model, normalized and WITH its unit, e.g. '5 kW'",
    )
    raw_text: Optional[str] = Field(
        default=None, description="the label/value exactly as printed on the sheet"
    )
    present: bool = Field(default=True, description="False if this field is absent on the sheet")
    confidence: Confidence = Field(
        default=Confidence.medium,
        description="low if the table layout made the 5 kW column hard to read",
    )
    note: Optional[str] = Field(
        default=None,
        description="anything odd: a value that looks inconsistent, ambiguous, or unclear",
    )


class DatasheetExtraction(BaseModel):
    """The vision model returns this for a single datasheet."""
    source_id: str = ""
    source_url: str = ""
    target_model_number: Optional[str] = Field(
        default=None, description="the full model number read for the 5 kW row"
    )
    variant_detected: Optional[str] = Field(
        default=None, description="variant from the title, e.g. AM2-P1 or AM2"
    )
    fields: list[ExtractedField] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Layer 2 -- the two sheets reconciled
# --------------------------------------------------------------------------
class ReconciledField(BaseModel):
    key: str
    label: str
    category: Category
    status: ReconStatus
    values: dict[str, Optional[str]]        # source_id -> normalized value
    raw: dict[str, Optional[str]]           # source_id -> raw text
    confidence: dict[str, Confidence]       # source_id -> confidence
    note: Optional[str] = None


class SourceMeta(BaseModel):
    id: str
    url: str
    variant_expected: Optional[str] = None
    variant_detected: Optional[str] = None
    revision_hint: Optional[str] = None


class ReconciliationResult(BaseModel):
    target_model: str
    target_power: str
    generated_at: str
    sources: list[SourceMeta]
    fields: list[ReconciledField]
    notes: list[str] = Field(default_factory=list)
