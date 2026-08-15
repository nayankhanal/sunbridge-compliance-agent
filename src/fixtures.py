"""Test data for --mock runs and the reconcile tests.

These are hand-written values, NOT pipeline output - they let the reconcile/draft
half run without a key or network. They mirror the two real Deye sheets (5 kW
column, conflicts included) so the mock draft shows every status.
"""
from __future__ import annotations

from .schema import Confidence, DatasheetExtraction, ExtractedField as EF

# Values shared by both sheets for the 5 kW column (they agree on these).
_SHARED = {
    "rated_output_power": "5 kW",
    "rated_ac_output_current": "7.6/7.3 A",
    "max_ac_output_current": "8.4/8 A",
    "output_voltage_range": "220/380V, 230/400V (0.85–1.1 Un)",
    "grid_frequency": "50/60 Hz",
    "phase": "Three Phase",
    "mppt_trackers_strings": "2 / 1+1",
    "max_efficiency": "98.3 %",
    "euro_efficiency": "98.1 %",
    "max_dc_input_power": "6.5 kW",
    "mppt_voltage_range": "120-1000 V",
    "ip_rating": "IP65",
    "dimensions": "283x463x178 mm",
    "operating_temp_range": "-25 to +60 °C",
    "warranty": "5 Years",
    "manufacturer_name": "Ningbo Deye Inverter Technology Co., Ltd.",
    "manufacturer_address": "No. 26 South YongJiang Road, Daqi, Beilun, Ningbo, Zhejiang, China",
    "country_of_manufacture": "China",
}


def _shared_fields() -> list[EF]:
    return [EF(key=k, value=v, confidence=Confidence.high) for k, v in _SHARED.items()]


def mock_extractions() -> list[DatasheetExtraction]:
    am2p1 = DatasheetExtraction(
        source_id="AM2-P1", source_url="https://example/am2-p1.pdf",
        variant_detected="AM2-P1", target_model_number="SUN-5K-G06P3-EU-AM2-P1",
        fields=_shared_fields() + [
            EF(key="model_number", value="SUN-5K-G06P3-EU-AM2-P1", confidence=Confidence.high),
            EF(key="max_power", value="5.5 kW", raw_text="Max. Active Power (kW): 5.5",
               confidence=Confidence.high),
            EF(key="topology", value="Transformerless", confidence=Confidence.high),
            EF(key="cooling", value="Free Cooling", confidence=Confidence.high),
            EF(key="weight", value="11 kg", raw_text="Weight (kg): 11", confidence=Confidence.high),
            EF(key="grid_connection_standards",
               value="IEC 61727, IEC 62116, EN 50549", confidence=Confidence.medium),
            EF(key="safety_emc_standards",
               value="IEC/EN 61000-6-1/2/3/4, IEC/EN 62109-1, IEC/EN 62109-2",
               confidence=Confidence.medium),
            EF(key="overvoltage_category", value=None, present=False),
        ],
    )
    am2 = DatasheetExtraction(
        source_id="AM2", source_url="https://example/am2.pdf",
        variant_detected="AM2", target_model_number="SUN-5K-G06P3-EU-AM2",
        fields=_shared_fields() + [
            EF(key="model_number", value="SUN-5K-G06P3-EU-AM2", confidence=Confidence.high),
            EF(key="max_power", value="5.5 kVA",
               raw_text="Max. AC Output Apparent Power (kVA): 5.5", confidence=Confidence.high),
            EF(key="topology", value="Non-Isolated", confidence=Confidence.high),
            EF(key="cooling", value="Natural Cooling", confidence=Confidence.high),
            EF(key="weight", value="11 kg", raw_text="Weight (kg): 4.8  ...  11",
               confidence=Confidence.low,
               note="Sheet prints weight twice with different numbers (4.8 and 11) — "
                    "inconsistent; 4.8 kg is implausible for this unit."),
            EF(key="grid_connection_standards",
               value="IEC 61727, IEC 62116, CEI 0-21, EN 50549, NRS 097",
               confidence=Confidence.medium),
            EF(key="safety_emc_standards",
               value="IEC/EN 62109-1, IEC/EN 62109-2", confidence=Confidence.medium),
            EF(key="overvoltage_category", value="OVC II(DC), OVC III(AC)",
               confidence=Confidence.medium),
        ],
    )
    return [am2p1, am2]
