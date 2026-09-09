"""Comprehensive test suite for Forecast Input -> Reliability Analysis Pipeline.

Validates:
1. Canonical forecast input contract (issuance-time only, strict anti-leakage).
2. Domain identification (spatial basin, lead horizon, variable validation).
3. Calibrated probability for supported/validated domains (Bay of Bengal/Arabian Sea, 6h-48h).
4. Honest abstention for unsupported/unvalidated domains (D+3 to D+10, extra-basin).
5. Disentanglement of confidence status vs probability status.
6. Audited feature telemetry with explicit physical units.
7. Fail-safe data quality tiers and non-fabrication guarantees.
8. Upload and analysis API endpoints.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.inference import (
    CanonicalForecastInput,
    EnsembleMemberInput,
    LiveInferenceResponse,
)
from backend.app.services.inference_engine import production_engine

client = TestClient(app)


import math

def make_bay_of_bengal_members(count: int = 11, base_lat: float = 14.5, base_lon: float = 87.0):
    """Generate realistic synoptic vortex fixes in the Bay of Bengal."""
    members = []
    for i in range(1, count + 1):
        angle = 2 * math.pi * (i - 1) / max(1, count)
        lat = base_lat + 0.7 * math.sin(angle)
        lon = base_lon + 1.1 * math.cos(angle)
        members.append(
            EnsembleMemberInput(
                member_id=i,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                central_pressure_hpa=round(992.0 + (i % 5), 1),
            )
        )
    return members


def make_north_atlantic_members(count: int = 11):
    """Generate synoptic vortex fixes in the North Atlantic."""
    members = []
    for i in range(1, count + 1):
        angle = 2 * math.pi * (i - 1) / max(1, count)
        lat = 25.0 + 0.7 * math.sin(angle)
        lon = -65.0 + 1.1 * math.cos(angle)
        members.append(
            EnsembleMemberInput(
                member_id=i,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                central_pressure_hpa=round(980.0 + (i % 5), 1),
            )
        )
    return members


# =========================================================================
# Case A: Supported Validated Domain (+24h, Bay of Bengal)
# =========================================================================
def test_case_a_supported_validated_forecast():
    """Supported domain (+24h Bay of Bengal) must return real calibrated probability."""
    members = make_bay_of_bengal_members(11)
    req = CanonicalForecastInput(
        forecast_source="NCMRWF TIGGE",
        model="NCMRWF_NEPS",
        forecast_cycle="2023-11-15T00:00:00Z",
        valid_time="2023-11-16T00:00:00Z",
        lead_hours=24,
        variable="Mean Sea Level Pressure (msl)",
        units="hPa",
        region="MAR_BOB",
        deterministic_lat=17.0,
        deterministic_lon=89.0,
        ensemble_members=members,
    )

    res = production_engine.evaluate(req)

    # 1. Validation & Quality
    assert res.status == "ok"
    assert res.validation_status == "VALID"
    assert res.data_quality == "DATA COMPLETE"

    # 2. Domain Identification
    assert res.domain_identified is not None
    assert res.domain_identified.basin == "Bay of Bengal"
    assert res.domain_identified.lead_classification == "SHORT_RANGE"
    assert res.domain_identified.is_validated_domain is True
    assert "Validated for Bay of Bengal" in res.domain_identified.validation_notes

    # 3. Calibrated Bust Probability (Authoritative M1 Baseline)
    assert res.bust_probability is not None
    assert 0.01 <= res.bust_probability <= 0.99
    assert res.probability_status == "CALIBRATED"
    assert res.calibration_status == "CALIBRATED"
    assert res.bust_risk_percent == int(round(res.bust_probability * 100))
    assert res.reliability_score is not None
    assert res.reliability_state in ["STABLE", "WATCH", "VULNERABLE", "SEVERE"]

    # 4. Confidence Status
    assert res.confidence_status in ["HIGH", "MODERATE"]

    # 5. Audited Feature Telemetry
    assert res.feature_telemetry is not None
    assert len(res.feature_telemetry) >= 4
    spread_item = next(item for item in res.feature_telemetry if item.name == "ensemble_spread")
    assert spread_item.unit == "km"
    assert spread_item.validation_status == "VALIDATED"
    assert spread_item.value > 0

    # 6. Strict Prospective Verification Status
    assert res.verification_status == "PENDING_VERIFICATION"


# =========================================================================
# Case B: Unsupported / Unvalidated Lead Horizon (+72h / D+3)
# =========================================================================
def test_case_b_unvalidated_lead_horizon_72h():
    """Unvalidated lead horizon (+72h / D+3) MUST honestly withhold bust probability."""
    members = make_bay_of_bengal_members(11)
    req = CanonicalForecastInput(
        forecast_source="NCMRWF TIGGE",
        model="NCMRWF_NEPS",
        forecast_cycle="2023-11-15T00:00:00Z",
        valid_time="2023-11-18T00:00:00Z",
        lead_hours=72,  # D+3 (Beyond 48h validated limit)
        variable="Mean Sea Level Pressure (msl)",
        units="hPa",
        region="MAR_BOB",
        ensemble_members=members,
    )

    res = production_engine.evaluate(req)

    # 1. Validation & Operational Status
    assert res.status == "not_validated"
    assert res.validation_status == "NOT_VALIDATED"
    assert res.data_quality == "DATA COMPLETE"

    # 2. Domain Identification
    assert res.domain_identified is not None
    assert res.domain_identified.lead_classification == "MEDIUM_RANGE"
    assert res.domain_identified.is_validated_domain is False
    assert "not validated for lead times > 48h" in res.domain_identified.validation_notes

    # 3. Honest Abstention: NEVER invent or manufacture probability
    assert res.bust_probability is None
    assert res.bust_risk_percent is None
    assert res.reliability_score is None
    assert res.probability_status == "NOT_VALIDATED"
    assert res.calibration_status == "NOT_VALIDATED"
    assert res.reliability_state == "UNVALIDATED_DOMAIN"

    # 4. Disentangled Confidence Status
    # Complete telemetry means data confidence is HIGH even though probability is NOT_VALIDATED
    assert res.confidence_status == "HIGH"

    # 5. Preserved Feature Telemetry & Explanations
    assert res.feature_telemetry is not None
    spread_item = next(item for item in res.feature_telemetry if item.name == "ensemble_spread")
    assert spread_item.validation_status == "UNVALIDATED"
    assert "Calibrated bust probability is withheld (NOT_VALIDATED)" in res.message


# =========================================================================
# Case C: Unsupported Spatial Domain (North Atlantic)
# =========================================================================
def test_case_c_unvalidated_spatial_domain_north_atlantic():
    """Spatial domain outside North Indian Ocean MUST withhold probability."""
    members = make_north_atlantic_members(11)
    req = CanonicalForecastInput(
        forecast_source="ECMWF IFS",
        model="ECMWF_IFS",
        forecast_cycle="2023-09-01T00:00:00Z",
        valid_time="2023-09-02T00:00:00Z",
        lead_hours=24,
        variable="Mean Sea Level Pressure (msl)",
        region="North Atlantic",
        ensemble_members=members,
    )

    res = production_engine.evaluate(req)

    assert res.domain_identified.is_validated_domain is False
    assert "North Atlantic" in res.domain_identified.basin
    assert res.bust_probability is None
    assert res.bust_risk_percent is None
    assert res.probability_status == "NOT_VALIDATED"
    assert res.calibration_status == "NOT_VALIDATED"
    assert "falls outside the validated North Indian Ocean basin" in res.domain_identified.validation_notes


# =========================================================================
# Case D: Insufficient Data (< 5 ensemble members)
# =========================================================================
def test_case_d_insufficient_ensemble_members():
    """Fewer than 5 members triggers fail-safe DATA INSUFFICIENT with null probability."""
    members = make_bay_of_bengal_members(3)
    req = CanonicalForecastInput(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-11-15T00:00:00Z",
        valid_time="2023-11-16T00:00:00Z",
        lead_hours=24,
        ensemble_members=members,
    )

    res = production_engine.evaluate(req)

    assert res.status == "insufficient_data"
    assert res.validation_status == "INSUFFICIENT"
    assert res.data_quality == "DATA INSUFFICIENT"
    assert res.bust_probability is None
    assert res.bust_risk_percent is None
    assert res.probability_status == "INSUFFICIENT_EVIDENCE"
    assert res.confidence_status == "INSUFFICIENT"
    assert res.reliability_state == "DATA_INSUFFICIENT"


# =========================================================================
# Case E: Strict Anti-Leakage (Rejection of Ground Truth Fields)
# =========================================================================
@pytest.mark.parametrize(
    "forbidden_field,val",
    [
        ("observed_lat", 15.0),
        ("observed_lon", 88.0),
        ("track_error_km", 42.5),
        ("ground_truth", True),
        ("is_bust", False),
        ("post_cutoff_observation", "2023-11-17T00:00:00Z"),
        ("confidence_quadrant", "QUADRANT_A"),
    ],
)
def test_case_e_anti_leakage_forbids_future_verification(forbidden_field, val):
    """Pydantic extra='forbid' MUST reject any ground-truth or future verification fields."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": 1, "latitude": 15.0, "longitude": 88.0, "central_pressure_hpa": 1000.0}
        ],
        forbidden_field: val,
    }
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 422


# =========================================================================
# Case F: Input Validation & Formatting
# =========================================================================
def test_case_f_rejects_invalid_units():
    """Unsupported physical units must be rejected."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "units": "furlongs_per_fortnight",
        "ensemble_members": [
            {"member_id": 1, "latitude": 15.0, "longitude": 88.0}
        ],
    }
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 422


def test_case_f_rejects_invalid_iso_timestamps():
    """Non-ISO timestamps must be rejected."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "15-11-2023 00:00",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": 1, "latitude": 15.0, "longitude": 88.0}
        ],
    }
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 422


# =========================================================================
# Case G: Upload API Endpoint
# =========================================================================
def test_case_g_upload_json_file():
    """Upload endpoint correctly processes a valid JSON forecast file."""
    members = [
        {"member_id": i, "latitude": 14.5 + 0.05 * i, "longitude": 87.0 + 0.05 * i, "central_pressure_hpa": 995.0}
        for i in range(1, 12)
    ]
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "variable": "Mean Sea Level Pressure (msl)",
        "region": "MAR_BOB",
        "ensemble_members": members,
    }

    file_bytes = io.BytesIO(json.dumps(payload).encode("utf-8"))
    response = client.post(
        "/api/v1/inference/upload",
        files={"file": ("forecast_payload.json", file_bytes, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["domain_identified"]["is_validated_domain"] is True
    assert data["probability_status"] == "CALIBRATED"
    assert data["bust_probability"] is not None


def test_case_g_upload_rejects_leakage_in_file():
    """Upload endpoint strictly rejects files with verification leakage fields."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "observed_lat": 14.5,  # Leakage!
        "ensemble_members": [],
    }
    file_bytes = io.BytesIO(json.dumps(payload).encode("utf-8"))
    response = client.post(
        "/api/v1/inference/upload",
        files={"file": ("leakage_payload.json", file_bytes, "application/json")},
    )
    assert response.status_code == 422


# =========================================================================
# Case H: Analyze Endpoint (Professor / Analyst Workflow)
# =========================================================================
def test_case_h_analyze_endpoint():
    """Canonical /analyze endpoint executes the full pipeline end-to-end."""
    members = [
        {"member_id": i, "latitude": 14.5 + 0.05 * i, "longitude": 87.0 + 0.05 * i, "central_pressure_hpa": 995.0}
        for i in range(1, 12)
    ]
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "model": "NCMRWF_NEPS",
        "forecast_cycle": "2023-11-15T00:00:00Z",
        "valid_time": "2023-11-16T00:00:00Z",
        "lead_hours": 24,
        "region": "Bay of Bengal",
        "ensemble_members": members,
    }
    response = client.post("/api/v1/inference/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "VALID"
    assert data["probability_status"] == "CALIBRATED"
    assert data["domain_identified"]["basin"] == "Bay of Bengal"
    assert "M1_SpreadOnly" in data["model_status"]
