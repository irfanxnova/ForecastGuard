"""Tests for Multi-Model Forecast Agreement & NWP Evidence Subsystem.

Verifies:
1. Data Audit correctly identifies NCMRWF NEPS as the sole archived model.
2. Missing model handling: <2 models deterministically returns INSUFFICIENT_EVIDENCE.
3. Zero models handling: Empty payload returns INSUFFICIENT_EVIDENCE.
4. Duplicate model rejection: Providing duplicate model IDs returns INSUFFICIENT_EVIDENCE.
5. Temporal misalignment rejection: Mismatched valid times return INSUFFICIENT_EVIDENCE.
6. Spatial bounds validation: Invalid coordinates handled gracefully.
7. Disagreement calculation: Exact deterministic great-circle track separation.
8. State transitions: Threshold transitions (AGREEMENT, MODERATE_DISAGREEMENT, HIGH_DISAGREEMENT).
9. Missing variable handling: Missing MSLP evaluates track distance without error.
10. Anti-fabrication audit: Confirms no synthetic or fabricated ECMWF/UKMO archives exist in repository.
11. Scientific non-overclaim: Rejects equate of model disagreement to "forecast error" or "failure".
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
import pytest

from scientific.ml.multimodel import (
    ModelForecastFix,
    MultiModelAgreementEngine,
    MultiModelAgreementResult,
    MultiModelAgreementState,
    NWPModelStatus,
    NWP_DATA_AUDIT_CATALOG,
    _haversine_distance,
    multimodel_engine,
)


def test_data_audit_identifies_ncmrwf_as_sole_available_model() -> None:
    """Verify data audit reports exactly 1 operational model and flags missing archives."""
    engine = MultiModelAgreementEngine()
    summary = engine.get_data_audit_summary()

    assert summary["available_operational_models"] == 1
    assert summary["missing_archive_models"] == 3
    assert summary["independent_cross_model_pairs"] == 0
    assert summary["decision_gate_status"] == "INSUFFICIENT_EVIDENCE"

    catalog = summary["catalog"]
    assert "NCMRWF_NEPS" in catalog
    assert catalog["NCMRWF_NEPS"]["status"] == NWPModelStatus.OPERATIONAL_ARCHIVED.value
    assert catalog["NCMRWF_NEPS"]["verified_cyclone_leads"] == 101

    assert "ECMWF_IFS" in catalog
    assert catalog["ECMWF_IFS"]["status"] == NWPModelStatus.MISSING_ARCHIVE.value
    assert catalog["ECMWF_IFS"]["verified_cyclone_leads"] == 0


def test_insufficient_evidence_when_single_model_provided() -> None:
    """Verify that providing only 1 model returns INSUFFICIENT_EVIDENCE with informative notice."""
    engine = MultiModelAgreementEngine()
    now = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    single_fix = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=now,
        forecast_lead_hours=24,
        valid_time=datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc),
        latitude=14.5,
        longitude=87.2,
        mslp_hpa=992.0,
    )

    result = engine.evaluate([single_fix])

    assert result.state == MultiModelAgreementState.INSUFFICIENT_EVIDENCE
    assert result.available_model_count == 1
    assert result.mean_track_separation_km is None
    assert result.max_track_separation_km is None
    assert "insufficient independent models" in result.agreement_notice
    assert "NCMRWF_NEPS" in result.agreement_notice
    assert result.validation_status == "INSUFFICIENT_EVIDENCE"
    assert result.is_abstention_recommended is False


def test_insufficient_evidence_when_zero_models_provided() -> None:
    """Verify that empty models list returns INSUFFICIENT_EVIDENCE safely."""
    engine = MultiModelAgreementEngine()
    result = engine.evaluate([])

    assert result.state == MultiModelAgreementState.INSUFFICIENT_EVIDENCE
    assert result.available_model_count == 0
    assert result.models_evaluated == []
    assert result.validation_status == "INSUFFICIENT_EVIDENCE"


def test_duplicate_model_rejection() -> None:
    """Verify that providing the same model twice does not masquerade as cross-model agreement."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_valid = datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc)

    fix1 = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=14.5,
        longitude=87.2,
    )
    fix2 = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=14.6,
        longitude=87.3,
    )

    result = engine.evaluate([fix1, fix2])

    assert result.state == MultiModelAgreementState.INSUFFICIENT_EVIDENCE
    assert "duplicate model identifiers" in result.agreement_notice


def test_temporal_misalignment_rejection() -> None:
    """Verify that models with mismatched valid times return INSUFFICIENT_EVIDENCE."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)

    fix_ncmrwf = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc),
        latitude=14.5,
        longitude=87.2,
    )
    fix_ecmwf = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=30,
        valid_time=datetime(2023, 10, 21, 18, 0, tzinfo=timezone.utc),  # 6h difference!
        latitude=14.8,
        longitude=87.5,
    )

    result = engine.evaluate([fix_ncmrwf, fix_ecmwf])

    assert result.state == MultiModelAgreementState.INSUFFICIENT_EVIDENCE
    assert "Temporal misalignment" in result.agreement_notice


def test_spatial_bounds_and_nan_validation() -> None:
    """Verify that NaN or out-of-bounds coordinates return INSUFFICIENT_EVIDENCE."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_valid = datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc)

    fix_valid = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=14.5,
        longitude=87.2,
    )
    fix_nan = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=float("nan"),
        longitude=87.2,
    )

    result = engine.evaluate([fix_valid, fix_nan])
    assert result.state == MultiModelAgreementState.INSUFFICIENT_EVIDENCE
    assert "Invalid coordinates" in result.agreement_notice


def test_deterministic_cross_model_distance_calculation() -> None:
    """Verify exact, deterministic Haversine distance and MSLP difference calculation."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_valid = datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc)

    # Coords: (15.0N, 88.0E) vs (15.0N, 88.5E)
    # Distance: Earth radius 6371 km * cos(15 deg) * (0.5 * pi / 180) ~ 53.64 km
    fix1 = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.0,
        longitude=88.0,
        mslp_hpa=988.0,
    )
    fix2 = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.0,
        longitude=88.5,
        mslp_hpa=992.0,
    )

    result1 = engine.evaluate([fix1, fix2])
    result2 = engine.evaluate([fix1, fix2])

    assert result1.state == MultiModelAgreementState.AGREEMENT
    assert result1.max_track_separation_km is not None
    assert 52.0 < result1.max_track_separation_km < 55.0
    assert result1.mslp_disagreement_hpa == 4.0
    # Determinism
    assert result1.max_track_separation_km == result2.max_track_separation_km
    assert result1.mslp_disagreement_hpa == result2.mslp_disagreement_hpa
    assert result1.state == result2.state


def test_disagreement_state_transitions() -> None:
    """Verify deterministic transitions across AGREEMENT, MODERATE, and HIGH DISAGREEMENT."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_valid = datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc)

    # 1. Close fix: ~30 km -> AGREEMENT
    fix_base = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.0,
        longitude=88.0,
        mslp_hpa=990.0,
    )
    fix_close = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.2,
        longitude=88.1,
        mslp_hpa=993.0,
    )
    res_agree = engine.evaluate([fix_base, fix_close])
    assert res_agree.state == MultiModelAgreementState.AGREEMENT

    # 2. Moderate fix: ~100 km -> MODERATE_DISAGREEMENT
    fix_moderate = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.9,
        longitude=88.0,
        mslp_hpa=990.0,
    )
    res_mod = engine.evaluate([fix_base, fix_moderate])
    assert res_mod.state == MultiModelAgreementState.MODERATE_DISAGREEMENT

    # 3. Distant fix: ~250 km -> HIGH_DISAGREEMENT
    fix_distant = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=17.2,
        longitude=88.0,
        mslp_hpa=990.0,
    )
    res_high = engine.evaluate([fix_base, fix_distant])
    assert res_high.state == MultiModelAgreementState.HIGH_DISAGREEMENT


def test_missing_variable_handling() -> None:
    """Verify that if MSLP is missing, track distance alone determines state without error."""
    engine = MultiModelAgreementEngine()
    t_init = datetime(2023, 10, 20, 12, 0, tzinfo=timezone.utc)
    t_valid = datetime(2023, 10, 21, 12, 0, tzinfo=timezone.utc)

    fix1 = ModelForecastFix(
        model_id="NCMRWF_NEPS",
        center="NCMRWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.0,
        longitude=88.0,
        mslp_hpa=None,  # missing MSLP
    )
    fix2 = ModelForecastFix(
        model_id="ECMWF_IFS",
        center="ECMWF",
        initialization_time=t_init,
        forecast_lead_hours=24,
        valid_time=t_valid,
        latitude=15.1,
        longitude=88.0,
        mslp_hpa=None,  # missing MSLP
    )

    result = engine.evaluate([fix1, fix2])
    assert result.state == MultiModelAgreementState.AGREEMENT
    assert result.mslp_disagreement_hpa is None
    assert result.max_track_separation_km is not None


def test_no_fabricated_model_data_in_repository() -> None:
    """Verify that no fabricated, simulated, or fake NWP model archives exist in repository data."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_dir = repo_root / "data"

    # Search for forbidden synthetic files
    forbidden_stems = ["fake_ecmwf", "simulated_ukmo", "ecmwf_cyclone", "ukmo_cyclone"]
    for path in data_dir.rglob("*"):
        if path.is_file():
            name_lower = path.name.lower()
            for stem in forbidden_stems:
                assert stem not in name_lower, f"Forbidden synthetic model file detected: {path}"


def test_scientific_qualification_non_overclaim() -> None:
    """Verify that multi-model engine avoids equating disagreement with forecast error or failure."""
    engine = MultiModelAgreementEngine()
    summary = engine.get_data_audit_summary()

    forbidden_phrases = [
        "model disagreement = error",
        "model disagreement = failure",
        "model disagreement causes",
        "guaranteed bust",
    ]

    for phrase in forbidden_phrases:
        assert phrase not in summary["decision_gate_reason"].lower()

    # Check sample evaluation notice
    res = engine.evaluate([])
    for phrase in forbidden_phrases:
        assert phrase not in res.agreement_notice.lower()
