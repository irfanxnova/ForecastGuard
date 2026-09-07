"""Scientific unit tests for Production Inference Engine (M1_SpreadOnly) and Data Fail-Safe."""

import math
import pytest
from backend.app.schemas.inference import EnsembleMemberInput, LiveInferenceRequest
from backend.app.services.inference_engine import production_engine
from backend.app.services.model_config import (
    M0_CLIMATOLOGY_METADATA,
    M1_PARAMETERS,
    M1_SPREAD_ONLY_METADATA,
    RESEARCH_MODELS_CATALOG,
)


def _make_sample_request(member_count: int = 11, spread_delta: float = 0.05, lead: int = 24) -> LiveInferenceRequest:
    members = [
        EnsembleMemberInput(
            member_id=i,
            latitude=12.0 + (i - 6) * spread_delta,
            longitude=85.0 + (i - 6) * spread_delta,
            central_pressure_hpa=990.0 + i,
        )
        for i in range(1, member_count + 1)
    ]
    return LiveInferenceRequest(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-12-01T00:00:00Z",
        valid_time="2023-12-02T00:00:00Z",
        lead_hours=lead,
        ensemble_members=members,
    )


def test_production_model_governance():
    """Verify primary baseline is M1 and M0 is operational reference."""
    assert M1_SPREAD_ONLY_METADATA.model_name == "M1_SpreadOnly"
    assert M1_SPREAD_ONLY_METADATA.scientific_status == "PRIMARY_MACHINE_BASELINE"
    assert M0_CLIMATOLOGY_METADATA.scientific_status == "OPERATIONAL_REFERENCE"

    # Verify candidate models in catalog are explicitly non-production
    provisional = [m for m in RESEARCH_MODELS_CATALOG if m["scientific_status"] == "PROVISIONAL_CANDIDATE"]
    assert len(provisional) == 3  # M2, M3, M6
    diagnostic = [m for m in RESEARCH_MODELS_CATALOG if "DIAGNOSTIC" in m["scientific_status"]]
    assert len(diagnostic) == 2  # M4, M5


def test_inference_engine_deterministic_output():
    """Verify that inference engine produces deterministic, reproducible predictions."""
    req = _make_sample_request(11, 0.05, 24)
    res1 = production_engine.evaluate(req)
    res2 = production_engine.evaluate(req)

    assert res1.bust_risk_percent == res2.bust_risk_percent
    assert res1.reliability_score == res2.reliability_score
    assert res1.reliability_state == res2.reliability_state
    assert res1.features_extracted == res2.features_extracted


def test_inference_engine_failsafe_zero_members():
    """Verify fail-safe behavior when 0 ensemble members are passed."""
    req = LiveInferenceRequest(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-12-01T00:00:00Z",
        valid_time="2023-12-02T00:00:00Z",
        lead_hours=24,
        ensemble_members=[],
    )
    res = production_engine.evaluate(req)
    assert res.data_quality == "DATA INSUFFICIENT"
    assert res.reliability_state == "DATA_INSUFFICIENT"
    assert res.bust_risk_percent is None
    assert res.reliability_score is None
    assert "insufficient forecast evidence" in res.message


def test_inference_engine_failsafe_degraded_members():
    """Verify fail-safe transitions to DATA DEGRADED when 5-10 members are present."""
    for count in [5, 7, 10]:
        req = _make_sample_request(count, 0.05, 24)
        res = production_engine.evaluate(req)
        assert res.data_quality == "DATA DEGRADED"
        assert res.reliability_state in ["STABLE", "WATCH", "VULNERABLE", "SEVERE"]
        assert res.bust_risk_percent is not None


def test_inference_engine_failsafe_complete_members():
    """Verify complete 11-member ensemble yields DATA COMPLETE."""
    req = _make_sample_request(11, 0.05, 24)
    res = production_engine.evaluate(req)
    assert res.data_quality == "DATA COMPLETE"
    assert res.provenance.processing_status == "DATA COMPLETE"
    assert res.provenance.ensemble_member_count == "11 ensemble members"
