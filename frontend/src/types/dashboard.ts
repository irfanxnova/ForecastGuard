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
    representationState?: "WELL_REPRESENTED" | "LOW_SUPPORT" | "NOVEL_STATE" | "INSUFFICIENT_EVIDENCE";
    supportScore?: number;
    representationDistance?: number | null;
    abstentionRecommended?: boolean;
    supportNotice?: string;
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
