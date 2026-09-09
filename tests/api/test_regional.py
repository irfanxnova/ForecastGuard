"""API Tests for Regional Reliability Endpoints (/api/v1/regional)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_regional_cases():
    """Verify supported cases catalog endpoint."""
    resp = client.get("/api/v1/regional/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) >= 6
    case_ids = {c["case_id"] for c in cases}
    assert "MIDHILI_00Z" in case_ids
    assert "MICHAUNG_00Z" in case_ids
    assert "BIPARJOY_00Z" in case_ids

    # Check case contract
    c0 = cases[0]
    assert "case_id" in c0
    assert "available_leads" in c0
    assert "unsupported_leads" in c0
    assert "supported_regions" in c0
    assert "unsupported_regions" in c0


def test_regional_assessment_valid_midhili_d1():
    """Verify regional assessment for MIDHILI at D+1 (+24h)."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == "MIDHILI_00Z"
    assert data["lead_time"] == "D+1"
    assert data["lead_hours"] == 24
    assert data["is_horizon_supported"] is True
    assert data["data_quality"] == "DATA COMPLETE"
    assert len(data["regions"]) == 7

    # Find Bay of Bengal assessment
    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None
    assert bob["reliability_state"] in ["STABLE", "WATCH", "DEGRADING", "HIGH_RISK"]
    assert bob["bust_probability"] is not None
    assert 0.0 <= bob["bust_probability"] <= 1.0
    assert bob["reliability_score"] is not None
    assert 0 <= bob["reliability_score"] <= 100
    assert bob["evidence_status"] == "COMPLETE"
    assert len(bob["dominant_evidence"]) == 3
    assert bob["provenance"]["ensemble_member_count"] == 11
    assert bob["provenance"]["grid_cells_in_region"] > 0

    # Find Arabian Sea assessment (must be strictly INSUFFICIENT_EVIDENCE)
    as_reg = next((r for r in data["regions"] if r["region_id"] == "MAR_AS"), None)
    assert as_reg is not None
    assert as_reg["reliability_state"] == "INSUFFICIENT_EVIDENCE"
    assert as_reg["bust_probability"] is None
    assert as_reg["reliability_score"] is None
    assert as_reg["evidence_status"] == "UNAVAILABLE"
    assert "outside spatial coverage" in as_reg["status_message"].lower()


def test_regional_assessment_valid_midhili_d2_trend():
    """Verify D+2 evaluation calculates genuine trend from D+1."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+2")
    assert resp.status_code == 200
    data = resp.json()

    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None
    # Midhili D+2 has rapid downstream acceleration, so bust vulnerability increases
    assert bob["trend"] == "increasing"
    assert "increased" in bob["trend_description"].lower()


def test_regional_assessment_unsupported_horizon_honesty():
    """Verify D+5 produces honest INSUFFICIENT_EVIDENCE with zero fabricated numbers."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+5")
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_horizon_supported"] is False
    assert data["data_quality"] == "DATA INSUFFICIENT"
    assert data["supported_regions_count"] == 0

    for reg in data["regions"]:
        assert reg["reliability_state"] == "INSUFFICIENT_EVIDENCE"
        assert reg["bust_probability"] is None
        assert reg["reliability_score"] is None
        assert reg["trend"] == "unavailable"
        assert "not validated" in reg["status_message"].lower()


def test_get_single_region():
    """Verify single-region focused rail endpoint."""
    resp = client.get("/api/v1/regional/region/MAR_BOB?case_id=MIDHILI_00Z&lead_time=D+1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "MAR_BOB"
    assert data["region_name"] == "Bay of Bengal Basin"
    assert data["bust_probability"] is not None


def test_unknown_case_returns_404():
    """Verify invalid case returns clean 404."""
    resp = client.get("/api/v1/regional/assessment?case_id=NONEXISTENT_CASE")
    assert resp.status_code == 404


def test_regional_model_semantics_and_calibration_status():
    """Verify scientific model semantics, calibration status, and ground-truth verification (Attempt 2)."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    assert resp.status_code == 200
    data = resp.json()

    # 1. Verified Region (MAR_BOB has official IMD Best Track ground truth at D+1)
    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None
    assert bob["model_status"] == "VALIDATED"
    assert bob["calibration_status"] == "CALIBRATED"
    assert bob["verification_status"] == "VERIFIED"
    assert bob["raw_model_score"] is not None
    assert 0.0 <= bob["raw_model_score"] <= 1.0
    assert bob["calibrated_bust_probability"] is not None
    assert 0.0 <= bob["calibrated_bust_probability"] <= 1.0
    assert bob["bust_probability"] == bob["calibrated_bust_probability"]
    assert bob["verification_detail"] is not None
    assert bob["verification_detail"]["case_id"] == "MIDHILI_00Z"
    assert bob["verification_detail"]["is_bust"] is True
    assert bob["verification_detail"]["track_error_km"] > 0
    assert bob["provenance"]["model_name"] == "V2_Regional_Calibrated_Platt"

    # 2. Unverified in-domain region (IND_SOU is covered by GRIB but has no cyclone fix)
    south_ind = next((r for r in data["regions"] if r["region_id"] == "IND_SOU"), None)
    assert south_ind is not None
    assert south_ind["model_status"] == "CANDIDATE"
    assert south_ind["calibration_status"] == "UNCALIBRATED_CANDIDATE"
    assert south_ind["verification_status"] == "UNVERIFIED"
    assert south_ind["raw_model_score"] is not None
    assert south_ind["calibrated_bust_probability"] is None
    assert south_ind["bust_probability"] is None  # Never expose raw score under probability label
    assert south_ind["verification_detail"] is None

    # 3. Out-of-domain region (MAR_AS is outside GRIB grid)
    arabian_sea = next((r for r in data["regions"] if r["region_id"] == "MAR_AS"), None)
    assert arabian_sea is not None
    assert arabian_sea["model_status"] == "INSUFFICIENT_EVIDENCE"
    assert arabian_sea["calibration_status"] == "NOT_AVAILABLE"
    assert arabian_sea["raw_model_score"] is None
    assert arabian_sea["calibrated_bust_probability"] is None
    assert arabian_sea["bust_probability"] is None
    assert arabian_sea["verification_detail"] is None


def test_regional_case_verification_endpoint():
    """Verify ground-truth verification endpoint /api/v1/regional/verification/{case_id}."""
    resp = client.get("/api/v1/regional/verification/MIDHILI_00Z")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "MIDHILI_00Z"
    assert data["storm_name"] == "MIDHILI"
    assert data["verified_leads_count"] == 8
    assert data["bust_count"] == 6
    assert "IMD" in data["data_source"]

    # Check verification record contract
    rec0 = data["records"][0]
    assert rec0["case_id"] == "MIDHILI_00Z"
    assert rec0["lead_hours"] == 6
    assert rec0["region_id"] == "MAR_BOB"
    assert rec0["track_error_km"] > 0
    assert rec0["threshold_km"] > 0
    assert isinstance(rec0["is_bust"], bool)
    assert "forecast_lat" in rec0 and "observed_lat" in rec0

    # Non-existent case returns 404
    err_resp = client.get("/api/v1/regional/verification/NONEXISTENT_STORM")
    assert err_resp.status_code == 404


def test_regional_features_catalog_endpoint_and_assessment():
    """Verify explicit regional features catalog and definitions (Priority 3)."""
    # 1. Test standalone catalog endpoint
    feat_resp = client.get("/api/v1/regional/features")
    assert feat_resp.status_code == 200
    catalog = feat_resp.json()
    assert len(catalog) == 5

    names = {f["feature_name"] for f in catalog}
    expected_names = {
        "regional_mean_spread",
        "peak_spread_anomaly",
        "pairwise_member_disagreement",
        "lead_time_hours",
        "trend_delta",
    }
    assert names == expected_names

    for feat in catalog:
        assert feat["definition"] != ""
        assert feat["units"] in ["Pa", "hours", "dimensionless"]
        assert feat["source"] != ""
        assert feat["is_validated"] is True
        assert feat["model_role"] != ""

    # 2. Test feature items inside regional assessment payload
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    data = resp.json()
    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None
    assert len(bob["regional_features"]) == 5

    feat_dict = {f["feature_name"]: f for f in bob["regional_features"]}
    assert feat_dict["regional_mean_spread"]["current_value"] > 0
    assert feat_dict["regional_mean_spread"]["units"] == "Pa"
    assert feat_dict["peak_spread_anomaly"]["current_value"] >= feat_dict["regional_mean_spread"]["current_value"]
    assert feat_dict["pairwise_member_disagreement"]["current_value"] > 0
    assert feat_dict["lead_time_hours"]["current_value"] == 24.0

