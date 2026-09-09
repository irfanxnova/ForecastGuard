/**
 * TypeScript definitions for Medium-Range Reliability Timeline and Confidence System.
 * Matches backend schemas in backend/app/schemas/inference.py.
 */

export type ProbabilityStatus = "CALIBRATED" | "NOT_VALIDATED" | "INSUFFICIENT_EVIDENCE" | "UNAVAILABLE";
export type AssessmentConfidence = "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT";
export type DataQualityTier = "DATA COMPLETE" | "DATA DEGRADED" | "DATA INSUFFICIENT";
export type EvidenceStrengthTier = "STRONG" | "MODERATE" | "WEAK" | "INSUFFICIENT";
export type HorizonValidationStatus = "VALID" | "PARTIAL" | "NOT_VALIDATED" | "INSUFFICIENT";
export type TrajectoryEvolutionState = "IMPROVING" | "STABLE" | "DEGRADING" | "MIXED" | "INSUFFICIENT_EVIDENCE";

export interface ConfidenceComponent {
  status: string;
  reason: string;
  source: string;
}

export interface ConfidenceBreakdown {
  data_coverage: ConfidenceComponent;
  model_validation: ConfidenceComponent;
  historical_representation: ConfidenceComponent;
  ensemble_support: ConfidenceComponent;
  provenance: ConfidenceComponent;
}

export interface StructuredExplanation {
  why: string;
  what_changed?: string | null;
  why_now: string;
}

export interface FeatureTelemetryItem {
  name: string;
  value: number;
  unit: string;
  source: string;
  availability: string;
  validation_status: string;
}

export interface NoveltyAssessment {
  representation_state: "WELL_REPRESENTED" | "LOW_SUPPORT" | "NOVEL_STATE" | "INSUFFICIENT_EVIDENCE";
  distance: number;
  nearest_historical_case: string;
  quantile: number;
  status: string;
  abstention_recommended: boolean;
  scientific_notice: string;
  support_dimensions?: Record<string, number>;
}

export interface MultiModelEvidence {
  state: "INSUFFICIENT_EVIDENCE" | "AGREEMENT" | "MODERATE_DISAGREEMENT" | "HIGH_DISAGREEMENT";
  models_evaluated: string[];
  available_model_count: number;
  valid_time?: string | null;
  forecast_cycle?: string | null;
  lead_hours?: number | null;
  mean_track_separation_km?: number | null;
  max_track_separation_km?: number | null;
  pairwise_separations_km?: Record<string, number>;
  mslp_disagreement_hpa?: number | null;
  agreement_notice: string;
  validation_status: string;
  is_abstention_recommended: boolean;
}

export interface TimelineLeadPoint {
  lead_name: string; // "D+1", "D+2", ..., "D+10"
  lead_hours: number; // 24, 48, ..., 240
  valid_time: string; // ISO 8601 UTC
  reliability_state: "STABLE" | "WATCH" | "VULNERABLE" | "SEVERE" | "DATA_INSUFFICIENT" | "UNVALIDATED_DOMAIN" | null;
  bust_probability: number | null; // 0.0 - 1.0 or null
  probability_status: ProbabilityStatus;
  assessment_confidence: AssessmentConfidence;
  data_quality: DataQualityTier;
  evidence_strength: EvidenceStrengthTier;
  validation_status: HorizonValidationStatus;
  support_index: number | null; // 0 - 100
  confidence_breakdown: ConfidenceBreakdown;
  structured_explanation: StructuredExplanation;
  evidence_summary: string;
  features_extracted?: Record<string, number> | null;
  feature_telemetry?: FeatureTelemetryItem[] | null;
  novelty_assessment?: NoveltyAssessment | null;
  multimodel_evidence?: MultiModelEvidence | null;
}

export interface LeadTransitionDelta {
  from_lead: string;
  to_lead: string;
  delta_hours: number;
  delta_spread_km?: number | null;
  delta_prob?: number | null;
  direction: string;
  summary: string;
}

export interface RiskEvolution {
  trajectory_state: TrajectoryEvolutionState;
  summary: string;
  evidence_basis: string[];
  lead_transitions: LeadTransitionDelta[];
}

export interface DomainIdentification {
  basin: string;
  region: string;
  lead_classification: string;
  is_validated_domain: boolean;
  validation_notes: string;
}

export interface MediumRangeForecastAnalysisResponse {
  status: "ok" | "partial_data" | "insufficient_data" | "not_validated";
  forecast_source: string;
  forecast_cycle: string;
  overall_assessment: {
    trustworthiness: string;
    dominant_state: string;
    validated_lead_count: number;
    unvalidated_lead_count: number;
    total_leads_evaluated: number;
    abstention_advised: boolean;
    operational_advisory: string;
  };
  timeline: TimelineLeadPoint[];
  risk_evolution: RiskEvolution;
  confidence: ConfidenceBreakdown;
  domain_identified: DomainIdentification;
  evidence_summary: {
    mean_ensemble_spread_km?: number | null;
    evaluated_leads: number;
    max_divergence_km?: number | null;
    multi_model_agreement?: string;
  };
  provenance: {
    engine: string;
    calibration_cohort: string;
    anti_leakage_guarantee: string;
    evaluated_at_utc: string;
  };
}

export interface EnsembleMemberInput {
  member_id: string;
  latitude: number;
  longitude: number;
  mslp_hpa?: number;
  wind_speed_kts?: number;
}

export interface CanonicalForecastInput {
  forecast_source: string;
  model?: string;
  forecast_cycle: string;
  lead_hours: number;
  valid_time: string;
  variable?: string;
  units?: string;
  latitude?: number;
  longitude?: number;
  region?: string;
  value?: number;
  deterministic_lat?: number;
  deterministic_lon?: number;
  ensemble_members: EnsembleMemberInput[];
}

export interface MultiLeadForecastInput {
  forecast_source: string;
  model?: string;
  forecast_cycle: string;
  variable?: string;
  units?: string;
  region?: string;
  leads: CanonicalForecastInput[];
}
