export type ReliabilityState =
  | "STABLE"
  | "WATCH"
  | "VULNERABLE"
  | "SEVERE"
  | "DEGRADING"
  | "HAZARDOUS"
  | "AWAITING_VERIFIED_CASE"
  | "DATA_INSUFFICIENT";

export interface TrajectoryPoint {
  lead: string; // "+06h", "+12h", "D+1", etc.
  score: number | null; // 0 to 100 or null if unverified
  state: ReliabilityState;
  isActionableSignal?: boolean;
  isFailureWindow?: boolean;
  description?: string;
}

export interface EvidenceFactor {
  id: string;
  rank: string;
  title: string;
  description: string;
  level: "HIGH" | "MODERATE" | "LOW" | "PENDING";
  icon: "divergence" | "drift" | "disagreement" | "regime";
}

export interface HistoricalAnalogue {
  id: string;
  date: string;
  similarity: number;
  outcome: string;
  riskZone: string;
}

export interface EnsembleMemberForecast {
  lead: string;
  values: number[]; // 11 member values
  mean: number;
  spreadStd: number;
}

export interface DataSourceStatus {
  name: string;
  status: "available" | "partial" | "pending";
  detail?: string;
}

export interface MapHotspot {
  id: string;
  x: number; // SVG coordinate percent
  y: number; // SVG coordinate percent
  name: string;
  leadWindow: string;
  description: string;
  riskPercent: number;
}

export interface CycloneLeadRecord {
  storm_id: string;
  storm_name: string;
  basin: string;
  cycle_label: string;
  initialization_time: string;
  forecast_lead_hours: number;
  forecast_valid_time: string;
  observed_lat: number;
  observed_lon: number;
  observed_pressure_hpa: number;
  forecast_lat: number;
  forecast_lon: number;
  forecast_pressure_hpa: number;
  track_error_km: number;
  threshold_km: number;
  bust_label: number;
  severity: "NORMAL" | "MODERATE" | "DEGRADED" | "SEVERE";
  ensemble_spread_km: number;
  ensemble_divergence_km: number;
  anisotropy_ratio: number;
  major_axis_spread_km: number;
  bimodality_coefficient: number;
  dominant_cluster_fraction: number;
  cluster_separation_km: number;
  spread_growth_km: number;
  spread_acceleration_km: number;
  trajectory_speed_kmh: number;
  trajectory_curvature_deg: number;
  anisotropy_growth_rate: number;
  trajectory_instability_km: number;
  has_prior_cycle: number;
  cycle_revision_distance_km: number | null;
  cycle_spread_shift_km: number | null;
  reliability_contradiction_index: number;
  confidence_quadrant: string;
  prospective_bust_within24h: number | null;
  prospective_error_plus6h: number | null;
  prospective_error_plus12h: number | null;
  prospective_error_plus24h: number | null;
  provenance: string;
}

export interface DashboardState {
  isDemoMode: boolean;
  activeStormName?: string;
  activeCycleLabel?: string;
  isObservationRevealed?: boolean;
  cycle: {
    model: string;
    initTime: string;
    dateFormatted: string;
    targetLead: string;
    validWindow: string;
    lastUpdateUtc: string;
  };
  reliability: {
    state: ReliabilityState;
    subtitle: string;
    bustRiskPercent: number | null;
    deltaPercent: number | null;
    firstActionableSignal: string;
    firstActionableSignalDesc: string;
    expectedFailureWindow: string;
    expectedFailureWindowDesc: string;
    evidenceConfidence: number | null;
    evidenceConfidenceDesc: string;
    keyMessage: string;
  };
  trajectory: TrajectoryPoint[];
  evidenceFactors: EvidenceFactor[];
  historicalAnalogues: HistoricalAnalogue[];
  ensembleSeries: EnsembleMemberForecast[];
  dataStatus: DataSourceStatus[];
  hotspot: MapHotspot | null;
  selectedLead: string;
  selectedVariable: string;
  selectedView: string;
  leadsData?: CycloneLeadRecord[];
  continuousErrorSummary?: {
    mean_km: number;
    median_km: number;
    max_km: number;
    min_km: number;
  };
}

// ---------------------------------------------------------------------------
// V2 Canonical Regional Reliability Interfaces
// ---------------------------------------------------------------------------

export type CanonicalReliabilityState =
  | "STABLE"
  | "WATCH"
  | "DEGRADING"
  | "HIGH_RISK"
  | "INSUFFICIENT_EVIDENCE";

export interface DominantEvidenceSignal {
  signal_id: string;
  rank: string;
  title: string;
  description: string;
  level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "UNAVAILABLE";
  metric_value?: number | null;
  metric_unit?: string | null;
}

export interface RegionalProvenanceData {
  forecast_source: string;
  forecast_cycle: string;
  valid_time: string;
  lead_time: string;
  lead_hours: number;
  ensemble_member_count: number;
  grid_cells_in_region: number;
  variable: string;
  model_name: string;
  model_version: string;
  feature_version: string;
  prediction_cutoff: string;
  data_quality_tier: "DATA COMPLETE" | "DATA DEGRADED" | "DATA INSUFFICIENT";
}

export interface RegionalFeatureCatalogItem {
  feature_name: string;
  definition: string;
  units: string;
  source: string;
  is_validated: boolean;
  model_role: string;
  current_value?: number | null;
}

export interface RegionalVerificationDetail {
  case_id: string;
  storm_name: string;
  lead_hours: number;
  lead_label: string;
  valid_time: string;
  region_id: string;
  region_name: string;
  forecast_lat: number;
  forecast_lon: number;
  forecast_pressure_hpa: number;
  observed_lat: number;
  observed_lon: number;
  observed_pressure_hpa: number;
  track_error_km: number;
  pressure_error_hpa: number;
  threshold_km: number;
  is_bust: boolean;
  severity: "NORMAL" | "MODERATE" | "DEGRADED" | "SEVERE";
  provenance: string;
}

export type EnsembleState =
  | "COHERENT"
  | "SPREADING"
  | "MULTI_BRANCH"
  | "FRAGMENTED"
  | "INSUFFICIENT_EVIDENCE";

export type TrajectoryState =
  | "STABLE_PERSISTENT"
  | "PROGRESSIVE_DRIFT"
  | "OSCILLATING_JUMPY"
  | "RAPID_REVISION"
  | "INSUFFICIENT_EVIDENCE";

export interface EnsembleIntelligenceSummary {
  state: EnsembleState;
  state_description: string;
  member_count: number;
  mean_spread?: number | null;
  spread_unit: string;
  coherence_score?: number | null;
  anisotropy_ratio?: number | null;
  bimodality_coefficient?: number | null;
  dominant_cluster_fraction?: number | null;
  cluster_separation?: number | null;
  pairwise_disagreement?: number | null;
  status: "COMPLETE" | "PARTIAL" | "INSUFFICIENT";
}

export interface TrajectoryIntelligenceSummary {
  state: TrajectoryState;
  state_description: string;
  has_prior_cycle: boolean;
  reference_cycle?: string | null;
  cycle_revision_distance_km?: number | null;
  cycle_spread_shift_km?: number | null;
  revision_rate_kmh?: number | null;
  trajectory_speed_kmh?: number | null;
  trajectory_curvature_deg?: number | null;
  spread_growth_rate?: number | null;
  trajectory_instability_km?: number | null;
  status: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "INSUFFICIENT";
}

export type EnvironmentalState =
  | "SYMMETRIC_DEEP_PRESSURE_STRUCTURE"
  | "MARGINAL_PRESSURE_STRUCTURE"
  | "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE"
  | "INSUFFICIENT_EVIDENCE";

export interface EnvironmentalIntelligenceSummary {
  state: EnvironmentalState;
  state_description: string;
  pressure_depth_hpa?: number | null;
  pressure_gradient_hpa_per_100km?: number | null;
  gradient_asymmetry_hpa_per_100km?: number | null;
  gradient_trend_hpa_per_100km?: number | null;
  core_pressure_hpa?: number | null;
  peripheral_pressure_hpa?: number | null;
  upper_air_shear_status: "AVAILABLE" | "UNAVAILABLE" | "INSUFFICIENT_EVIDENCE";
  mid_level_humidity_status: "AVAILABLE" | "UNAVAILABLE" | "INSUFFICIENT_EVIDENCE";
  sst_status: "AVAILABLE" | "UNAVAILABLE" | "INSUFFICIENT_EVIDENCE";
  validation_status: "VALIDATED" | "EXPERIMENTAL" | "INSUFFICIENT_EVIDENCE";
  provenance: string;
  scientific_provenance_note?: string;
  status: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "INSUFFICIENT";
}

export interface StructuredEvidenceObject {
  ensemble: EnsembleIntelligenceSummary;
  trajectory: TrajectoryIntelligenceSummary;
  environmental?: EnvironmentalIntelligenceSummary | null;
  trend: "increasing" | "decreasing" | "stable" | "unavailable";
  why_now: string;
  what_changed: string;
  evidence_status: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "INSUFFICIENT";
  evidence_strength: "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT_EVIDENCE";
  source_provenance: string;
}

export interface CanonicalRegionalAssessment {
  region_id: string;
  region_name: string;
  forecast_cycle: string;
  valid_time: string;
  lead_time: string;
  lead_hours: number;
  variable: string;
  model_status: "VALIDATED" | "CANDIDATE" | "INSUFFICIENT_EVIDENCE";
  calibration_status: "CALIBRATED" | "UNCALIBRATED_CANDIDATE" | "NOT_AVAILABLE";
  raw_model_score?: number | null;
  calibrated_bust_probability?: number | null;
  bust_probability: number | null;
  reliability_score: number | null;
  reliability_state: CanonicalReliabilityState;
  trend: "increasing" | "decreasing" | "stable" | "unavailable";
  trend_description?: string | null;
  assessment_confidence: "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT_EVIDENCE";
  evidence_status: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "INSUFFICIENT";
  dominant_evidence: DominantEvidenceSignal[];
  regional_features?: RegionalFeatureCatalogItem[];
  provenance: RegionalProvenanceData;
  verification_status: "VERIFIED" | "PENDING_VERIFICATION" | "UNVERIFIED";
  verification_detail?: RegionalVerificationDetail | null;
  domain_coverage_percent: number;
  status_message: string;
  ensemble_state?: EnsembleState | null;
  trajectory_state?: TrajectoryState | null;
  environmental_state?: EnvironmentalState | null;
  structured_evidence?: StructuredEvidenceObject | null;
  ensemble_intelligence?: EnsembleIntelligenceSummary | null;
  trajectory_intelligence?: TrajectoryIntelligenceSummary | null;
  environmental_intelligence?: EnvironmentalIntelligenceSummary | null;
}

export interface RegionalCaseSummary {
  case_id: string;
  storm_name?: string | null;
  basin: string;
  forecast_cycle: string;
  available_leads: string[];
  unsupported_leads: string[];
  available_variables: string[];
  supported_regions: string[];
  unsupported_regions: string[];
  description: string;
}

export interface RegionalAssessmentResponse {
  case_id: string;
  forecast_cycle: string;
  valid_time: string;
  lead_time: string;
  lead_hours: number;
  variable: string;
  available_leads: string[];
  unsupported_leads: string[];
  is_horizon_supported: boolean;
  regions: CanonicalRegionalAssessment[];
  supported_regions_count: number;
  unsupported_regions_count: number;
  data_quality: string;
  system_overview: string;
}

export interface StateTransitionEvent {
  transition_id: string;
  lead_hours: number;
  valid_time: string;
  from_state: CanonicalReliabilityState;
  to_state: CanonicalReliabilityState;
  probability_delta: number;
  severity_direction: "DEGRADING" | "IMPROVING" | "STABLE";
  trigger_reason: string;
}

export interface FirstActionableSignal {
  alert_triggered: boolean;
  signal_cutoff_iso?: string | null;
  signal_lead_hours?: number | null;
  trigger_state?: string | null;
  trigger_probability?: number | null;
  downstream_failure_time_iso?: string | null;
  downstream_failure_lead_hours?: number | null;
  warning_lead_hours?: number | null;
  warning_lead_label?: string | null;
  narrative: string;
}

export interface KnowledgeBoundaryStatus {
  cutoff_iso: string;
  elapsed_hours: number;
  available_observations_count: number;
  future_observations_locked_count: number;
  future_information_locked: boolean;
  unlocked_valid_times: string[];
  locked_valid_times: string[];
  boundary_statement: string;
}

export interface CycleComparison {
  prior_cycle_iso?: string | null;
  current_cycle_iso: string;
  region_id: string;
  target_lead_hours: number;
  risk_change?: number | null;
  risk_trend: "increasing" | "decreasing" | "stable" | "unavailable";
  state_change?: string | null;
  mean_spread_pa_change?: number | null;
  peak_spread_pa_change?: number | null;
  summary_narrative: string;
}

export interface RegionalTimelineStep {
  lead_hours: number;
  lead_label: string;
  valid_time: string;
  raw_model_score?: number | null;
  calibrated_bust_probability?: number | null;
  reliability_score?: number | null;
  reliability_state: CanonicalReliabilityState;
  trend: "increasing" | "decreasing" | "stable" | "unavailable";
  model_status: "VALIDATED" | "CANDIDATE" | "INSUFFICIENT_EVIDENCE";
  calibration_status: "CALIBRATED" | "UNCALIBRATED_CANDIDATE" | "NOT_AVAILABLE";
  verification_status: "VERIFIED" | "PENDING_VERIFICATION" | "UNVERIFIED";
  verification_detail?: RegionalVerificationDetail | null;
  is_alert_active: boolean;
  ensemble_state?: EnsembleState | null;
  trajectory_state?: TrajectoryState | null;
  environmental_state?: EnvironmentalState | null;
}

export interface RegionalTimelineResponse {
  case_id: string;
  region_id: string;
  region_name: string;
  forecast_cycle: string;
  steps: RegionalTimelineStep[];
  state_transitions: StateTransitionEvent[];
  first_actionable_signal?: FirstActionableSignal | null;
  cycle_comparison?: CycleComparison | null;
}

export interface ReplayStepDetail {
  step_index: number;
  cutoff_time: string;
  elapsed_hours: number;
  label: string;
  lead_hours: number;
  lead_label: string;
  knowledge_boundary: KnowledgeBoundaryStatus;
  focused_region_assessment: CanonicalRegionalAssessment;
  all_regional_assessments: CanonicalRegionalAssessment[];
  unlocked_verifications: RegionalVerificationDetail[];
  first_actionable_signal?: FirstActionableSignal | null;
  active_event?: string | null;
}

export interface ReplayCaseResponse {
  case_id: string;
  storm_name?: string | null;
  basin: string;
  forecast_cycle: string;
  total_steps: number;
  available_cutoffs: string[];
  steps: ReplayStepDetail[];
  first_actionable_signal?: FirstActionableSignal | null;
  overall_verification_summary: string;
}

