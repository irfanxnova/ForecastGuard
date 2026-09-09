"""Service layer for Multi-Model Forecast Agreement & NWP Data Audit."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.schemas.multimodel import (
    DataAuditSummaryResponse,
    ModelForecastFixInput,
    MultiModelEvidenceRequest,
    MultiModelEvidenceResponse,
    NWPModelAuditResponse,
)
from scientific.ml import (
    ModelForecastFix,
    MultiModelAgreementEngine,
    multimodel_engine,
)


class MultiModelService:
    """Singleton service wrapping the scientific MultiModelAgreementEngine."""

    def __init__(self, engine: Optional[MultiModelAgreementEngine] = None) -> None:
        self.engine = engine or multimodel_engine

    def get_data_audit(self) -> DataAuditSummaryResponse:
        """Return the structured NWP data audit summary."""
        raw = self.engine.get_data_audit_summary()
        catalog_dict = {
            k: NWPModelAuditResponse(**v) for k, v in raw["catalog"].items()
        }
        return DataAuditSummaryResponse(
            total_models_cataloged=raw["total_models_cataloged"],
            available_operational_models=raw["available_operational_models"],
            missing_archive_models=raw["missing_archive_models"],
            independent_cross_model_pairs=raw["independent_cross_model_pairs"],
            decision_gate_status=raw["decision_gate_status"],
            decision_gate_reason=raw["decision_gate_reason"],
            catalog=catalog_dict,
        )

    def evaluate_agreement(self, request: MultiModelEvidenceRequest) -> MultiModelEvidenceResponse:
        """Evaluate cross-model agreement for a list of input model fixes."""
        scientific_fixes = [
            ModelForecastFix(
                model_id=m.model_id,
                center=m.center,
                initialization_time=m.initialization_time,
                forecast_lead_hours=m.forecast_lead_hours,
                valid_time=m.valid_time,
                latitude=m.latitude,
                longitude=m.longitude,
                mslp_hpa=m.mslp_hpa,
                max_wind_kts=m.max_wind_kts,
            )
            for m in request.models
        ]
        result = self.engine.evaluate(scientific_fixes)
        return MultiModelEvidenceResponse(
            state=result.state.value,
            models_evaluated=result.models_evaluated,
            available_model_count=result.available_model_count,
            valid_time=result.valid_time,
            forecast_cycle=result.forecast_cycle,
            lead_hours=result.lead_hours,
            mean_track_separation_km=result.mean_track_separation_km,
            max_track_separation_km=result.max_track_separation_km,
            pairwise_separations_km=result.pairwise_separations_km,
            mslp_disagreement_hpa=result.mslp_disagreement_hpa,
            agreement_notice=result.agreement_notice,
            validation_status=result.validation_status,
            is_abstention_recommended=result.is_abstention_recommended,
            provenance=result.provenance,
        )

    def evaluate_live_cyclone_fix(
        self,
        model_id: str,
        center: str,
        initialization_time: datetime,
        forecast_lead_hours: int,
        valid_time: datetime,
        latitude: float,
        longitude: float,
        mslp_hpa: Optional[float] = None,
    ) -> MultiModelEvidenceResponse:
        """Evaluate multi-model evidence for a single operational model fix."""
        fix = ModelForecastFixInput(
            model_id=model_id,
            center=center,
            initialization_time=initialization_time,
            forecast_lead_hours=forecast_lead_hours,
            valid_time=valid_time,
            latitude=latitude,
            longitude=longitude,
            mslp_hpa=mslp_hpa,
        )
        return self.evaluate_agreement(MultiModelEvidenceRequest(models=[fix]))


multimodel_service = MultiModelService()
