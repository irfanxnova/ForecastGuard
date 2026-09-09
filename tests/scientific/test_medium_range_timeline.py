"""Comprehensive automated test suite for Medium-Range Reliability Timeline and Confidence System.

Verifies the 19 prompt test criteria:
1. D+1 validated probability calculation.
2. D+2 validated probability calculation.
3. D+3 returns NOT_VALIDATED rather than extrapolated probability.
4. D+10 returns NOT_VALIDATED or INSUFFICIENT_EVIDENCE depending on actual input availability.
5. Confidence remains distinct from probability.
6. OOD state does not become bust probability.
7. Missing ensemble data is handled honestly.
8. Multiple lead times produce chronological timeline.
9. Missing lead times remain missing.
10. Risk evolution does not falsely infer degradation from lead alone.
11. WHY references actual available evidence.
12. WHAT_CHANGED uses actual sequential data.
13. Ground-truth leakage remains rejected.
14. Existing inference tests remain passing.
15. Existing replay tests remain passing.
16. Existing regional tests remain passing.
17. Existing historical-memory tests remain passing.
18. Existing novelty/OOD tests remain passing.
19. Existing multi-model tests remain passing.
"""

import io
import json
import math
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.inference import (
    CanonicalForecastInput,
    EnsembleMemberInput,
    MultiLeadForecastInput,
    MediumRangeForecastAnalysisResponse,
)
from backend.app.services.inference_engine import production_engine

client = TestClient(app)


def build_lead_members(count: int = 11, base_lat: float = 14.5, base_lon: float = 87.0, spread_factor: float = 1.0):
    """Generate realistic 2D ensemble vortex fixes in Bay of Bengal with adjustable spread."""
    members = []
    for i in range(1, count + 1):
        angle = 2 * math.pi * (i - 1) / max(1, count)
        lat = base_lat + 0.7 * spread_factor * math.sin(angle)
        lon = base_lon + 1.1 * spread_factor * math.cos(angle)
        members.append(
            EnsembleMemberInput(
                member_id=i,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                central_pressure_hpa=round(992.0 + (i % 5), 1),
            )
        )
    return members


def build_test_lead(lead_hours: int, member_count: int = 11, spread_factor: float = 1.0) -> CanonicalForecastInput:
    """Helper to construct a single valid canonical forecast lead."""
    return CanonicalForecastInput(
        forecast_source="NCMRWF TIGGE",
        model="NCMRWF_NEPS",
        forecast_cycle="2023-11-15T00:00:00Z",
        valid_time=f"2023-11-{(15 + lead_hours // 24):02d}T00:00:00Z",
        lead_hours=lead_hours,
        variable="Mean Sea Level Pressure (msl)",
        units="hPa",
        region="MAR_BOB",
        deterministic_lat=17.0,
        deterministic_lon=89.0,
        ensemble_members=build_lead_members(member_count, 14.5, 87.0, spread_factor),
    )


# =========================================================================
# 1 & 2. D+1 and D+2 Validated Probability Calculation
# =========================================================================
def test_criterion_1_and_2_validated_d1_and_d2():
    """D+1 (+24h) and D+2 (+48h) in validated domain return calibrated bust probability."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=24, spread_factor=0.8),
            build_test_lead(lead_hours=48, spread_factor=1.2),
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)

    assert len(res.timeline) == 2
    d1 = res.timeline[0]
    d2 = res.timeline[1]

    assert d1.lead_name == "D+1"
    assert d1.lead_hours == 24
    assert d1.probability_status == "CALIBRATED"
    assert d1.validation_status == "VALID"
    assert d1.bust_probability is not None
    assert 0.01 <= d1.bust_probability <= 0.99
    assert d1.confidence_breakdown.model_validation.status == "VALIDATED_DOMAIN"

    assert d2.lead_name == "D+2"
    assert d2.lead_hours == 48
    assert d2.probability_status == "CALIBRATED"
    assert d2.validation_status == "VALID"
    assert d2.bust_probability is not None
    assert 0.01 <= d2.bust_probability <= 0.99
    assert d2.confidence_breakdown.model_validation.status == "VALIDATED_DOMAIN"


# =========================================================================
# 3. D+3 Returns NOT_VALIDATED rather than Extrapolated Probability
# =========================================================================
def test_criterion_3_d3_returns_not_validated_without_probability():
    """D+3 (+72h) MUST return probability_status='NOT_VALIDATED' and bust_probability=None."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=24),
            build_test_lead(lead_hours=48),
            build_test_lead(lead_hours=72),  # D+3
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)
    assert len(res.timeline) == 3
    d3 = res.timeline[2]

    assert d3.lead_name == "D+3"
    assert d3.lead_hours == 72
    assert d3.probability_status == "NOT_VALIDATED"
    assert d3.bust_probability is None  # NEVER fabricated!
    assert d3.reliability_state == "UNVALIDATED_DOMAIN"
    assert d3.confidence_breakdown.model_validation.status == "NOT_VALIDATED_HORIZON"
    assert "not validated for lead times > 48h" in d3.confidence_breakdown.model_validation.reason
    assert d3.structured_explanation.why_now.startswith("Forecast advances into the medium-range window")


# =========================================================================
# 4. D+10 Returns NOT_VALIDATED or INSUFFICIENT_EVIDENCE
# =========================================================================
def test_criterion_4_d10_handling_with_data_and_insufficient():
    """D+10 (+240h) returns NOT_VALIDATED when data is complete, or INSUFFICIENT_EVIDENCE when members < 5."""
    # With 11 members
    lead_d10_complete = build_test_lead(lead_hours=240, member_count=11)
    res_complete = production_engine.evaluate_timeline(
        MultiLeadForecastInput(forecast_cycle="2023-11-15T00:00:00Z", leads=[lead_d10_complete])
    )
    d10_point = res_complete.timeline[0]
    assert d10_point.lead_name == "D+10"
    assert d10_point.probability_status == "NOT_VALIDATED"
    assert d10_point.bust_probability is None
    assert d10_point.data_quality == "DATA COMPLETE"

    # With 3 members (< 5)
    lead_d10_sparse = build_test_lead(lead_hours=240, member_count=3)
    res_sparse = production_engine.evaluate_timeline(
        MultiLeadForecastInput(forecast_cycle="2023-11-15T00:00:00Z", leads=[lead_d10_sparse])
    )
    d10_sparse_point = res_sparse.timeline[0]
    assert d10_sparse_point.probability_status == "INSUFFICIENT_EVIDENCE"
    assert d10_sparse_point.bust_probability is None
    assert d10_sparse_point.data_quality == "DATA INSUFFICIENT"
    assert d10_sparse_point.assessment_confidence == "INSUFFICIENT"


# =========================================================================
# 5. Confidence Remains Distinct From Probability
# =========================================================================
def test_criterion_5_confidence_disentangled_from_probability():
    """Verify high data confidence exists at D+5 even when bust probability is honestly withheld."""
    lead_d5 = build_test_lead(lead_hours=120, member_count=11)
    res = production_engine.evaluate_timeline(
        MultiLeadForecastInput(forecast_cycle="2023-11-15T00:00:00Z", leads=[lead_d5])
    )
    point = res.timeline[0]

    # Confidence in evidence is HIGH (11 members present, clean data)
    assert point.assessment_confidence == "HIGH"
    assert point.confidence_breakdown.data_coverage.status == "COMPLETE"
    # But probability is honestly NOT_VALIDATED
    assert point.bust_probability is None
    assert point.probability_status == "NOT_VALIDATED"


# =========================================================================
# 6. OOD State Does Not Become Bust Probability
# =========================================================================
def test_criterion_6_ood_state_does_not_become_probability():
    """An unvalidated lead with NOVEL_STATE must NOT invent a high bust probability."""
    # Generate extreme wide dispersion to trigger NOVEL_STATE at D+4 (96h)
    lead_d4_novel = build_test_lead(lead_hours=96, member_count=11, spread_factor=5.0)
    res = production_engine.evaluate_timeline(
        MultiLeadForecastInput(forecast_cycle="2023-11-15T00:00:00Z", leads=[lead_d4_novel])
    )
    point = res.timeline[0]

    assert point.novelty_assessment is not None
    assert point.novelty_assessment.representation_state == "NOVEL_STATE"
    # Even though NOVEL_STATE, probability MUST NOT be manufactured
    assert point.bust_probability is None
    assert point.probability_status == "NOT_VALIDATED"


# =========================================================================
# 7. Missing Ensemble Data Handled Honestly
# =========================================================================
def test_criterion_7_missing_ensemble_data_handled_honestly():
    """Fewer than 5 members triggers fail-safe DATA INSUFFICIENT across all horizons."""
    lead_sparse = build_test_lead(lead_hours=24, member_count=2)
    res = production_engine.evaluate_timeline(
        MultiLeadForecastInput(forecast_cycle="2023-11-15T00:00:00Z", leads=[lead_sparse])
    )
    point = res.timeline[0]
    assert point.probability_status == "INSUFFICIENT_EVIDENCE"
    assert point.bust_probability is None
    assert point.reliability_state == "DATA_INSUFFICIENT"
    assert point.data_quality == "DATA INSUFFICIENT"
    assert point.evidence_strength == "INSUFFICIENT"


# =========================================================================
# 8. Multiple Lead Times Produce Chronological Timeline
# =========================================================================
def test_criterion_8_chronological_timeline_ordering():
    """Out-of-order leads are sorted strictly chronologically."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=96),  # D+4
            build_test_lead(lead_hours=24),  # D+1
            build_test_lead(lead_hours=48),  # D+2
            build_test_lead(lead_hours=72),  # D+3
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)
    assert len(res.timeline) == 4
    hours = [p.lead_hours for p in res.timeline]
    assert hours == [24, 48, 72, 96]
    labels = [p.lead_name for p in res.timeline]
    assert labels == ["D+1", "D+2", "D+3", "D+4"]


# =========================================================================
# 9. Missing Lead Times Remain Missing
# =========================================================================
def test_criterion_9_missing_leads_not_manufactured():
    """If input only has D+1 and D+4, intermediate D+2 and D+3 are NOT manufactured."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=24),  # D+1
            build_test_lead(lead_hours=96),  # D+4
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)
    assert len(res.timeline) == 2
    assert [p.lead_hours for p in res.timeline] == [24, 96]
    assert [p.lead_name for p in res.timeline] == ["D+1", "D+4"]


# =========================================================================
# 10. Risk Evolution Does Not Falsely Infer Degradation From Lead Alone
# =========================================================================
def test_criterion_10_risk_evolution_does_not_infer_from_lead_alone():
    """If spread remains flat or tightens, trajectory is STABLE or IMPROVING despite increasing lead."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=72, spread_factor=1.0),
            build_test_lead(lead_hours=96, spread_factor=0.98),
            build_test_lead(lead_hours=120, spread_factor=0.97),
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)
    # Lead time increased from 72 to 120h, but spread did NOT expand
    assert res.risk_evolution.trajectory_state in ["STABLE", "IMPROVING"]
    assert res.risk_evolution.trajectory_state != "DEGRADING"


# =========================================================================
# 11. WHY References Actual Available Evidence
# =========================================================================
def test_criterion_11_why_references_actual_evidence():
    """Structured WHY references actual spread in km and calibration domain status."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[build_test_lead(lead_hours=24, spread_factor=1.0)],
    )
    res = production_engine.evaluate_timeline(multi_input)
    p = res.timeline[0]
    why = p.structured_explanation.why
    assert "km" in why
    assert "ensemble spread" in why
    assert "regional calibration baseline" in why


# =========================================================================
# 12. WHAT_CHANGED Uses Actual Sequential Data
# =========================================================================
def test_criterion_12_what_changed_uses_sequential_deltas():
    """WHAT_CHANGED compares lead t with lead t-1 using delta values."""
    multi_input = MultiLeadForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        leads=[
            build_test_lead(lead_hours=24, spread_factor=0.8),
            build_test_lead(lead_hours=48, spread_factor=1.5),
        ],
    )
    res = production_engine.evaluate_timeline(multi_input)
    p1 = res.timeline[0]
    p2 = res.timeline[1]

    assert p1.structured_explanation.what_changed == "Initial lead horizon in the evaluated forecast sequence."
    what_changed_2 = p2.structured_explanation.what_changed
    assert "Relative to +24h" in what_changed_2
    assert "ensemble spread changed by" in what_changed_2


# =========================================================================
# 13. Ground-Truth Leakage Remains Rejected
# =========================================================================
def test_criterion_13_multi_lead_anti_leakage_rejects_verification():
    """MultiLeadForecastInput strictly forbids verification observations with 422."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "observed_track_error_km": 25.0,  # LEAKAGE
        "leads": [
            {
                "forecast_source": "NCMRWF TIGGE",
                "forecast_cycle": "2023-11-15T00:00:00Z",
                "valid_time": "2023-11-16T00:00:00Z",
                "lead_hours": 24,
                "ensemble_members": [],
            }
        ],
    }
    response = client.post("/api/v1/inference/timeline", json=payload)
    assert response.status_code == 422


# =========================================================================
# API Endpoint Integration: /timeline and /analyze
# =========================================================================
def test_api_timeline_endpoint():
    """POST /api/v1/inference/timeline endpoint executes successfully."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "leads": [
            {
                "forecast_source": "NCMRWF TIGGE",
                "forecast_cycle": "2023-11-15T00:00:00Z",
                "valid_time": "2023-11-16T00:00:00Z",
                "lead_hours": 24,
                "variable": "Mean Sea Level Pressure (msl)",
                "region": "MAR_BOB",
                "deterministic_lat": 17.0,
                "deterministic_lon": 89.0,
                "ensemble_members": [
                    {"member_id": i, "latitude": 14.5 + 0.1 * i, "longitude": 87.0 + 0.1 * i, "central_pressure_hpa": 995.0}
                    for i in range(1, 12)
                ],
            },
            {
                "forecast_source": "NCMRWF TIGGE",
                "forecast_cycle": "2023-11-15T00:00:00Z",
                "valid_time": "2023-11-18T00:00:00Z",
                "lead_hours": 72,
                "variable": "Mean Sea Level Pressure (msl)",
                "region": "MAR_BOB",
                "deterministic_lat": 18.0,
                "deterministic_lon": 90.0,
                "ensemble_members": [
                    {"member_id": i, "latitude": 16.5 + 0.1 * i, "longitude": 88.0 + 0.1 * i, "central_pressure_hpa": 990.0}
                    for i in range(1, 12)
                ],
            },
        ],
    }
    resp = client.post("/api/v1/inference/timeline", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["timeline"]) == 2
    assert data["timeline"][0]["lead_name"] == "D+1"
    assert data["timeline"][0]["probability_status"] == "CALIBRATED"
    assert data["timeline"][1]["lead_name"] == "D+3"
    assert data["timeline"][1]["probability_status"] == "NOT_VALIDATED"
    assert data["risk_evolution"]["trajectory_state"] in ["IMPROVING", "STABLE", "DEGRADING", "MIXED"]


def test_api_upload_multi_lead_file():
    """POST /api/v1/inference/upload handles multi-lead JSON file cleanly."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "leads": [
            {
                "forecast_source": "NCMRWF TIGGE",
                "forecast_cycle": "2023-11-15T00:00:00Z",
                "valid_time": "2023-11-16T00:00:00Z",
                "lead_hours": 24,
                "ensemble_members": [
                    {"member_id": i, "latitude": 14.5 + 0.1 * i, "longitude": 87.0 + 0.1 * i}
                    for i in range(1, 12)
                ],
            }
        ],
    }
    file_bytes = io.BytesIO(json.dumps(payload).encode("utf-8"))
    resp = client.post(
        "/api/v1/inference/upload",
        files={"file": ("multi_lead_forecast.json", file_bytes, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    assert len(data["timeline"]) == 1
