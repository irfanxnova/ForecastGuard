import React, { useState, useEffect, useCallback } from "react";
import {
  CanonicalRegionalAssessment,
  RegionalAssessmentResponse,
  RegionalCaseSummary,
} from "../types/dashboard";
import { RegionalHeroMap } from "./RegionalHeroMap";
import { HistoricalReplayHero } from "./HistoricalReplayHero";

interface CommandCenterProps {
  onInvestigateView: (viewName: string) => void;
  backendOnline: boolean;
}

const ALL_HORIZONS = ["D+1", "D+2", "D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"];

export const CommandCenter: React.FC<CommandCenterProps> = ({
  onInvestigateView,
  backendOnline,
}) => {
  const [activeMode, setActiveMode] = useState<"regional_overview" | "historical_replay">("regional_overview");
  const [cases, setCases] = useState<RegionalCaseSummary[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>("MIDHILI_00Z");
  const [activeLead, setActiveLead] = useState<string>("D+1");
  const [activeVariable, setActiveVariable] = useState<string>("Mean Sea Level Pressure (msl)");
  const [selectedRegionId, setSelectedRegionId] = useState<string>("MAR_BOB");
  const [assessmentData, setAssessmentData] = useState<RegionalAssessmentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch supported cases list
  useEffect(() => {
    let isMounted = true;
    async function fetchCases() {
      try {
        const res = await fetch("/api/v1/regional/cases");
        if (res.ok) {
          const data: RegionalCaseSummary[] = await res.json();
          if (isMounted && data.length > 0) {
            setCases(data);
          }
        }
      } catch (err) {
        // Fallback handled gracefully
      }
    }
    fetchCases();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch regional assessment when case, lead, or variable changes
  const fetchAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/v1/regional/assessment?case_id=${encodeURIComponent(
        activeCaseId
      )}&lead_time=${encodeURIComponent(activeLead)}&variable=${encodeURIComponent(activeVariable)}`;
      const res = await fetch(url);
      if (res.ok) {
        const data: RegionalAssessmentResponse = await res.json();
        setAssessmentData(data);
      } else {
        setError(`Failed to fetch assessment: HTTP ${res.status}`);
      }
    } catch (err) {
      setError("Backend connection error. Please ensure API service is active.");
    } finally {
      setLoading(false);
    }
  }, [activeCaseId, activeLead, activeVariable]);

  useEffect(() => {
    fetchAssessment();
  }, [fetchAssessment]);

  // Selected active case metadata
  const currentCase = cases.find((c) => c.case_id === activeCaseId) || {
    case_id: activeCaseId,
    storm_name: activeCaseId.split("_")[0],
    basin: "North Indian Ocean",
    forecast_cycle: "2023-11-16T00:00:00Z",
    available_leads: ["D+1", "D+2"],
    unsupported_leads: ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
    available_variables: ["Mean Sea Level Pressure (msl)"],
    supported_regions: ["MAR_BOB", "IND_ENE", "IND_SOU"],
    unsupported_regions: ["MAR_AS", "IND_WST", "IND_NW", "IND_CEN"],
    description: "Evaluated forecast run.",
  };

  // Selected region assessment object
  const selectedAssessment: CanonicalRegionalAssessment | null =
    assessmentData?.regions.find((r) => r.region_id === selectedRegionId) ||
    assessmentData?.regions[0] ||
    null;

  const ensIntel = selectedAssessment?.ensemble_intelligence || selectedAssessment?.structured_evidence?.ensemble;
  const trajIntel = selectedAssessment?.trajectory_intelligence || selectedAssessment?.structured_evidence?.trajectory;
  const envIntel = selectedAssessment?.environmental_intelligence || selectedAssessment?.structured_evidence?.environmental;
  const histIntel = selectedAssessment?.historical_memory || selectedAssessment?.structured_evidence?.historical_memory;
  const repIntel = selectedAssessment?.representation || selectedAssessment?.structured_evidence?.representation;
  const multiIntel = selectedAssessment?.multimodel || selectedAssessment?.structured_evidence?.multimodel;

  const isSelectedLeadAvailable = currentCase.available_leads.includes(activeLead);

  return (
    <div className="command-center-container">
      {/* 1. Compact Instrument Top Bar */}
      <header className="cc-topbar">
        <div className="cc-brand-group">
          <div className="cc-logo-badge">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#F5B83D" strokeWidth="2.2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            <span className="cc-brand-title">FORECASTGUARD</span>
            <span className="cc-version-pill">V2 COMMAND CENTER</span>
          </div>
          <span className="cc-brand-sub">Regional Reliability Intelligence</span>
        </div>

        {/* Case & Variable Selectors */}
        <div className="cc-selectors-group">
          <div className="cc-control-unit">
            <label className="cc-control-label">FORECAST CASE</label>
            <select
              className="cc-select cc-select-case"
              value={activeCaseId}
              onChange={(e) => {
                setActiveCaseId(e.target.value);
                // Default region based on case basin
                if (e.target.value.includes("BIPARJOY") || e.target.value.includes("TEJ")) {
                  setSelectedRegionId("MAR_AS");
                } else {
                  setSelectedRegionId("MAR_BOB");
                }
              }}
            >
              {cases.length > 0 ? (
                cases.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.storm_name ? `${c.storm_name} (${c.basin})` : c.case_id}
                  </option>
                ))
              ) : (
                <>
                  <option value="MIDHILI_00Z">MIDHILI (Bay of Bengal)</option>
                  <option value="MICHAUNG_00Z">MICHAUNG (Bay of Bengal Reference)</option>
                  <option value="BIPARJOY_00Z">BIPARJOY (Arabian Sea)</option>
                  <option value="HAMOON_00Z">HAMOON (Bay of Bengal)</option>
                  <option value="TEJ_00Z">TEJ (Arabian Sea)</option>
                  <option value="MOCHA_00Z">MOCHA (Bay of Bengal)</option>
                </>
              )}
            </select>
          </div>

          <div className="cc-control-unit">
            <label className="cc-control-label">VARIABLE</label>
            <select
              className="cc-select"
              value={activeVariable}
              onChange={(e) => setActiveVariable(e.target.value)}
            >
              <option value="Mean Sea Level Pressure (msl)">Pressure (msl)</option>
              <option value="Total Precipitation (tp)">Precipitation (tp)</option>
              <option value="2m Temperature (2t)">Temperature (2t)</option>
            </select>
          </div>

          <div className="cc-meta-badge">
            <span className="cc-meta-title">CYCLE</span>
            <span className="cc-meta-val">
              {assessmentData ? assessmentData.forecast_cycle.slice(0, 16).replace("T", " ") + "Z" : "2023-11-16 00Z"}
            </span>
          </div>

          <div className="cc-meta-badge">
            <span className="cc-meta-title">VALID TIME</span>
            <span className="cc-meta-val">
              {assessmentData ? assessmentData.valid_time.slice(0, 16).replace("T", " ") + "Z" : "--"}
            </span>
          </div>

          <div className={`cc-status-pill ${backendOnline ? "online" : "offline"}`}>
            <span className="status-dot"></span>
            <span>{backendOnline ? "LIVE BACKEND" : "FALLBACK"}</span>
          </div>

          {/* View Mode Selector */}
          <div className="cc-mode-selector-group">
            <button
              className={`cc-mode-tab-btn ${activeMode === "regional_overview" ? "active" : ""}`}
              onClick={() => setActiveMode("regional_overview")}
            >
              🗺️ REGIONAL COMMAND
            </button>
            <button
              className={`cc-mode-tab-btn ${activeMode === "historical_replay" ? "active" : ""}`}
              onClick={() => setActiveMode("historical_replay")}
            >
              ⏪ HISTORICAL REPLAY
            </button>
            <button
              className="cc-mode-tab-btn"
              style={{ borderColor: "#0ea5e9", color: "#38bdf8" }}
              onClick={() => onInvestigateView("timeline")}
              title="Launch Medium-Range D+1..D+10 Workflow"
            >
              ⏱️ TIMELINE (D+1..D+10)
            </button>
          </div>
        </div>
      </header>

      {activeMode === "historical_replay" ? (
        <HistoricalReplayHero
          initialCaseId={activeCaseId}
          onNavigateTab={onInvestigateView}
          backendOnline={backendOnline}
        />
      ) : (
        <>
          {/* 2. D+Lead Horizon Interaction Control Bar */}
          <div className="cc-horizon-bar">
        <div className="horizon-label-group">
          <span className="horizon-title">FORECAST LEAD HORIZON</span>
          <span className="horizon-sub">Select issuance lead step</span>
        </div>

        <div className="horizon-buttons-container">
          {ALL_HORIZONS.map((lead) => {
            const isAvailable = currentCase.available_leads.includes(lead);
            const isSelected = activeLead === lead;
            return (
              <button
                key={lead}
                className={`horizon-btn ${isSelected ? "selected" : ""} ${
                  isAvailable ? "validated" : "unsupported"
                }`}
                onClick={() => setActiveLead(lead)}
                title={
                  isAvailable
                    ? `Validated ${lead} telemetry available`
                    : `Horizon ${lead} beyond validated telemetry — Insufficient Evidence`
                }
              >
                <span className="horizon-btn-text">{lead}</span>
                {isAvailable ? (
                  <span className="validated-indicator" title="Validated Telemetry">●</span>
                ) : (
                  <span className="unsupported-tag">NO DATA</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="horizon-audit-note">
          {isSelectedLeadAvailable ? (
            <span className="audit-tag green">✓ VALIDATED PROSPECTIVE HORIZON (+{assessmentData?.lead_hours || 24}h)</span>
          ) : (
            <span
              className="audit-tag amber"
              style={{ cursor: "pointer" }}
              onClick={() => onInvestigateView("timeline")}
              title="Open Medium-Range Workflow"
            >
              ⚠ EXTENDED HORIZON &bull; OPEN MEDIUM-RANGE TIMELINE &rarr;
            </span>
          )}
        </div>
      </div>

      {/* 3. Operational Main Stage: Hero Map + Right Intelligence Rail */}
      <div className="cc-stage-layout">
        {/* Main Hero Map Stage */}
        <main className="cc-map-hero-panel">
          <div className="panel-header-compact">
            <div className="panel-title-wrap">
              <h2 className="panel-title-text">REGIONAL RELIABILITY FIELD</h2>
              <span className="panel-subtitle-text">
                {currentCase.description}
              </span>
            </div>

            <div className="coverage-counter">
              <span className="counter-item">
                <strong className="text-amber">{assessmentData?.supported_regions_count ?? 0}</strong> Regions Evaluated
              </span>
              <span className="counter-divider">|</span>
              <span className="counter-item">
                <strong className="text-muted">{assessmentData?.unsupported_regions_count ?? 0}</strong> Outside Domain
              </span>
            </div>
          </div>

          <div className="map-view-body">
            {loading ? (
              <div className="cc-loading-overlay">
                <div className="loading-spinner"></div>
                <span>Evaluating real GRIB ensemble fields...</span>
              </div>
            ) : error ? (
              <div className="cc-error-box">
                <span className="error-icon">⚠</span>
                <span>{error}</span>
                <button className="btn-retry" onClick={fetchAssessment}>
                  Retry
                </button>
              </div>
            ) : (
              <RegionalHeroMap
                assessments={assessmentData?.regions || []}
                selectedRegionId={selectedRegionId}
                onSelectRegion={(regId) => setSelectedRegionId(regId)}
                leadTime={activeLead}
                caseId={activeCaseId}
                variable={activeVariable}
              />
            )}
          </div>
        </main>

        {/* 4. Right Intelligence Rail: Focused Region Deep Telemetry */}
        <aside className="cc-intelligence-rail">
          {selectedAssessment ? (
            <div className="rail-content">
              {/* Region Header */}
              <div className="rail-section region-header-section">
                <div className="rail-tag-row">
                  <span className="rail-tag">{selectedAssessment.region_id}</span>
                  <span className="rail-horizon-tag">{selectedAssessment.lead_time}</span>
                  <span className={`rail-model-badge status-${(selectedAssessment.model_status || "candidate").toLowerCase()}`}>
                    {selectedAssessment.model_status === "VALIDATED" ? "VALIDATED MODEL" : (selectedAssessment.model_status || "CANDIDATE")}
                  </span>
                  <span className={`rail-calib-badge status-${(selectedAssessment.calibration_status || "uncalibrated_candidate").toLowerCase()}`}>
                    {selectedAssessment.calibration_status === "CALIBRATED" ? "CALIBRATED" : (selectedAssessment.calibration_status || "UNCALIBRATED").replace("_", " ")}
                  </span>
                  {selectedAssessment.verification_status === "VERIFIED" && (
                    <span className="rail-verif-badge">✓ IMD VERIFIED</span>
                  )}
                  <span className={`rail-state-badge state-${selectedAssessment.reliability_state.toLowerCase()}`}>
                    {selectedAssessment.reliability_state.replace("_", " ")}
                  </span>
                </div>
                <h3 className="rail-region-title">{selectedAssessment.region_name}</h3>
                <p className="rail-status-msg">{selectedAssessment.status_message}</p>
              </div>

              {/* Reliability Score & Bust Probability / Candidate Risk Score */}
              <div className="rail-section metrics-hero-section">
                <div className="metric-box probability-box">
                  {selectedAssessment.calibration_status === "CALIBRATED" ? (
                    <>
                      <span className="metric-caption">BUST PROBABILITY</span>
                      <div className="metric-val-row">
                        <span className="metric-large text-amber">
                          {Math.round((selectedAssessment.calibrated_bust_probability ?? selectedAssessment.bust_probability ?? 0) * 100)}%
                        </span>
                        <span className="metric-sub">Calibrated</span>
                      </div>
                      <div className="calib-note green">Platt Scaled (ECE: 0.0019 | Brier: 0.178)</div>
                      <div className="calib-raw-note">
                        Raw Score: {selectedAssessment.raw_model_score !== null && selectedAssessment.raw_model_score !== undefined
                          ? `${Math.round(selectedAssessment.raw_model_score * 100)}%`
                          : "N/A"}
                      </div>
                    </>
                  ) : (
                    <>
                      <span className="metric-caption">CANDIDATE RISK SCORE</span>
                      <div className="metric-val-row">
                        {selectedAssessment.raw_model_score !== null && selectedAssessment.raw_model_score !== undefined ? (
                          <>
                            <span className="metric-large text-amber">
                              {Math.round(selectedAssessment.raw_model_score * 100)}%
                            </span>
                            <span className="metric-sub">Candidate (Raw)</span>
                          </>
                        ) : (
                          <span className="metric-unavailable">N/A</span>
                        )}
                      </div>
                      <div className="calib-note muted">
                        {selectedAssessment.reliability_state === "INSUFFICIENT_EVIDENCE"
                          ? "Calibrated Prob: Insufficient Evidence"
                          : "Calibrated Prob: Uncalibrated Candidate"}
                      </div>
                    </>
                  )}
                </div>

                <div className="metric-box score-box">
                  <span className="metric-caption">RELIABILITY INDEX</span>
                  <div className="metric-val-row">
                    {selectedAssessment.reliability_score !== null ? (
                      <>
                        <span className="metric-large text-green">
                          {selectedAssessment.reliability_score}
                        </span>
                        <span className="metric-sub">/ 100</span>
                      </>
                    ) : (
                      <span className="metric-unavailable">N/A</span>
                    )}
                  </div>
                </div>
              </div>

              {/* OPERATIONAL QUESTION 1: WHY IS RELIABILITY DEGRADING? */}
              <div className="op-question-section highlight-degrade">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q1</span>
                    <span className="op-question-title">WHY IS RELIABILITY DEGRADING?</span>
                  </div>
                  <div className="state-badges-cluster">
                    {selectedAssessment.ensemble_state && (
                      <span className={`badge-ensemble ${selectedAssessment.ensemble_state.toLowerCase()}`} title="Ensemble State">
                        ENS: {selectedAssessment.ensemble_state.replace(/_/g, " ")}
                      </span>
                    )}
                    {selectedAssessment.trajectory_state && (
                      <span className={`badge-trajectory ${selectedAssessment.trajectory_state.toLowerCase()}`} title="Trajectory State">
                        TRAJ: {selectedAssessment.trajectory_state.replace(/_/g, " ")}
                      </span>
                    )}
                    {selectedAssessment.environmental_state && (
                      <span className={`badge-environmental ${selectedAssessment.environmental_state.toLowerCase()}`} title="Environmental State">
                        ENV: {selectedAssessment.environmental_state.replace(/_/g, " ")}
                      </span>
                    )}
                  </div>
                </div>

                {selectedAssessment.structured_evidence?.evidence_status === "INSUFFICIENT" ||
                selectedAssessment.reliability_state === "INSUFFICIENT_EVIDENCE" ? (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>
                      {selectedAssessment.structured_evidence?.why_now ||
                        "Candidate scoring only active for supported tropical cyclone basins. Insufficient evidence to synthesize degradation."}
                    </span>
                  </div>
                ) : (
                  <div className="op-narrative-box">
                    {selectedAssessment.structured_evidence?.why_now ||
                      selectedAssessment.status_message}
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 2: WHAT CHANGED? */}
              <div className="op-question-section highlight-what-changed">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q2</span>
                    <span className="op-question-title">WHAT CHANGED ACROSS CYCLES & LEADS?</span>
                  </div>
                  <span className={`trend-chip ${selectedAssessment.trend}`}>
                    {selectedAssessment.trend === "increasing"
                      ? "↗ VULNERABILITY INCREASING"
                      : selectedAssessment.trend === "decreasing"
                      ? "↘ RELIABILITY CONSOLIDATING"
                      : selectedAssessment.trend === "stable"
                      ? "→ STABLE PROFILE"
                      : "— UNAVAILABLE"}
                  </span>
                </div>

                <div className="op-narrative-box">
                  {selectedAssessment.structured_evidence?.what_changed ||
                    selectedAssessment.trend_description ||
                    "Prior cycle comparison unavailable for this horizon."}
                </div>

                {trajIntel && (
                  <div className="telemetry-grid-2col">
                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">CYCLE REVISION DISTANCE</span>
                      <span className="telemetry-metric-value text-amber">
                        {trajIntel.cycle_revision_distance_km !== null && trajIntel.cycle_revision_distance_km !== undefined
                          ? `${trajIntel.cycle_revision_distance_km.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Successive run vortex displacement</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">SPREAD SHIFT</span>
                      <span className="telemetry-metric-value text-cyan">
                        {trajIntel.cycle_spread_shift_km !== null && trajIntel.cycle_spread_shift_km !== undefined
                          ? `${trajIntel.cycle_spread_shift_km > 0 ? "+" : ""}${trajIntel.cycle_spread_shift_km.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Dispersion growth vs prior run</span>
                    </div>
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 3: HOW COHERENT IS THE ENSEMBLE? */}
              <div className="op-question-section highlight-ensemble">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q3</span>
                    <span className="op-question-title">HOW COHERENT IS THE ENSEMBLE?</span>
                  </div>
                  {ensIntel && ensIntel.coherence_score !== null && ensIntel.coherence_score !== undefined && (
                    <span className="telemetry-metric-value text-cyan" style={{ fontSize: "10px" }}>
                      Score: {ensIntel.coherence_score.toFixed(2)}
                    </span>
                  )}
                </div>

                {ensIntel ? (
                  <div className="telemetry-grid-3col">
                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">ANISOTROPY (A)</span>
                      <span className="telemetry-metric-value text-cyan">
                        {ensIntel.anisotropy_ratio !== null && ensIntel.anisotropy_ratio !== undefined
                          ? ensIntel.anisotropy_ratio.toFixed(2)
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Major/minor axis ratio</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">BIMODALITY (BC)</span>
                      <span className="telemetry-metric-value text-amber">
                        {ensIntel.bimodality_coefficient !== null && ensIntel.bimodality_coefficient !== undefined
                          ? ensIntel.bimodality_coefficient.toFixed(3)
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">
                        {ensIntel.bimodality_coefficient !== null && ensIntel.bimodality_coefficient !== undefined && ensIntel.bimodality_coefficient >= 0.555
                          ? "⚠ Bifurcation"
                          : "Unimodal"}
                      </span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">PAIR DISAGREEMENT</span>
                      <span className="telemetry-metric-value text-amber">
                        {ensIntel.pairwise_disagreement !== null && ensIntel.pairwise_disagreement !== undefined
                          ? `${ensIntel.pairwise_disagreement.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">55 member pairs</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">DOMINANT CLUSTER</span>
                      <span className="telemetry-metric-value text-green">
                        {ensIntel.dominant_cluster_fraction !== null && ensIntel.dominant_cluster_fraction !== undefined
                          ? `${Math.round(ensIntel.dominant_cluster_fraction * 100)}%`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Member consensus</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">CLUSTER SEPARATION</span>
                      <span className="telemetry-metric-value text-amber">
                        {ensIntel.cluster_separation !== null && ensIntel.cluster_separation !== undefined
                          ? `${ensIntel.cluster_separation.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Between-branch gap</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">TOTAL DISPERSION</span>
                      <span className="telemetry-metric-value text-amber">
                        {ensIntel.mean_spread !== null && ensIntel.mean_spread !== undefined
                          ? `${ensIntel.mean_spread.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">RMS member spread</span>
                    </div>
                  </div>
                ) : (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>Detailed 11-member ensemble geometry is only active within supported basins.</span>
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 4: IS THE FORECAST BECOMING UNSTABLE? */}
              <div className="op-question-section highlight-trajectory">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q4</span>
                    <span className="op-question-title">IS THE FORECAST BECOMING UNSTABLE?</span>
                  </div>
                  {selectedAssessment.trajectory_state && (
                    <span className={`badge-trajectory ${selectedAssessment.trajectory_state.toLowerCase()}`}>
                      {selectedAssessment.trajectory_state.replace(/_/g, " ")}
                    </span>
                  )}
                </div>

                {trajIntel ? (
                  <div className="telemetry-grid-2col">
                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">TRANSLATION SPEED</span>
                      <span className="telemetry-metric-value text-green">
                        {trajIntel.trajectory_speed_kmh !== null && trajIntel.trajectory_speed_kmh !== undefined
                          ? `${trajIntel.trajectory_speed_kmh.toFixed(1)} km/h`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Along-track propagation</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">STEP JITTER</span>
                      <span className="telemetry-metric-value text-orange">
                        {trajIntel.trajectory_instability_km !== null && trajIntel.trajectory_instability_km !== undefined
                          ? `${trajIntel.trajectory_instability_km.toFixed(1)} km`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Path acceleration volatility</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">REVISION RATE</span>
                      <span className="telemetry-metric-value text-amber">
                        {trajIntel.revision_rate_kmh !== null && trajIntel.revision_rate_kmh !== undefined
                          ? `${trajIntel.revision_rate_kmh.toFixed(1)} km/h`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Cycle-to-cycle revision velocity</span>
                    </div>

                    <div className="telemetry-metric-cell">
                      <span className="telemetry-metric-title">HEADING CURVATURE</span>
                      <span className="telemetry-metric-value text-cyan">
                        {trajIntel.trajectory_curvature_deg !== null && trajIntel.trajectory_curvature_deg !== undefined
                          ? `${trajIntel.trajectory_curvature_deg.toFixed(1)}°`
                          : "N/A"}
                      </span>
                      <span className="telemetry-metric-sub">Recurvature turn angle</span>
                    </div>
                  </div>
                ) : (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>Trajectory instability telemetry unavailable for this region/lead.</span>
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 5: WHAT ATMOSPHERIC SIGNAL IS PRESENT? (ENVIRONMENTAL EVIDENCE) */}
              <div className="op-question-section highlight-env">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q5</span>
                    <span className="op-question-title">WHAT ATMOSPHERIC SIGNAL IS PRESENT?</span>
                  </div>
                  {selectedAssessment.environmental_state && (
                    <span className={`badge-environmental ${selectedAssessment.environmental_state.toLowerCase()}`}>
                      {selectedAssessment.environmental_state.replace(/_/g, " ")}
                    </span>
                  )}
                </div>

                {envIntel && envIntel.state !== "INSUFFICIENT_EVIDENCE" ? (
                  <>
                    <div className="telemetry-grid-3col">
                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">RADIAL GRADIENT</span>
                        <span className="telemetry-metric-value text-amber">
                          {envIntel.pressure_gradient_hpa_per_100km !== null && envIntel.pressure_gradient_hpa_per_100km !== undefined
                            ? `${envIntel.pressure_gradient_hpa_per_100km.toFixed(2)}`
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">hPa / 100 km</span>
                      </div>

                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">PRESSURE DEPTH</span>
                        <span className="telemetry-metric-value text-cyan">
                          {envIntel.pressure_depth_hpa !== null && envIntel.pressure_depth_hpa !== undefined
                            ? `${envIntel.pressure_depth_hpa.toFixed(1)} hPa`
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">Annulus vs Core</span>
                      </div>

                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">DIRECTIONAL ASYMMETRY</span>
                        <span className="telemetry-metric-value text-orange">
                          {envIntel.gradient_asymmetry_hpa_per_100km !== null && envIntel.gradient_asymmetry_hpa_per_100km !== undefined
                            ? `${envIntel.gradient_asymmetry_hpa_per_100km.toFixed(2)}`
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">Pressure gradient asymmetry</span>
                      </div>

                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">CORE MSLP</span>
                        <span className="telemetry-metric-value text-green">
                          {envIntel.core_pressure_hpa !== null && envIntel.core_pressure_hpa !== undefined
                            ? `${envIntel.core_pressure_hpa.toFixed(1)} hPa`
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">Vortex minimum</span>
                      </div>

                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">PERIPHERAL MSLP</span>
                        <span className="telemetry-metric-value text-cyan">
                          {envIntel.peripheral_pressure_hpa !== null && envIntel.peripheral_pressure_hpa !== undefined
                            ? `${envIntel.peripheral_pressure_hpa.toFixed(1)} hPa`
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">300-600 km ring</span>
                      </div>

                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">GRADIENT TREND</span>
                        <span className="telemetry-metric-value text-amber">
                          {envIntel.gradient_trend_hpa_per_100km !== null && envIntel.gradient_trend_hpa_per_100km !== undefined
                            ? `${envIntel.gradient_trend_hpa_per_100km > 0 ? "+" : ""}${envIntel.gradient_trend_hpa_per_100km.toFixed(2)}`
                            : "—"}
                        </span>
                        <span className="telemetry-metric-sub">hPa/100km vs prior</span>
                      </div>
                    </div>

                    <div className="env-narrative-note">
                      <span className="env-desc-label">Physical Conditioning:</span> {envIntel.state_description}
                    </div>
                  </>
                ) : (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>Environmental pressure telemetry outside supported tropical cyclone basins.</span>
                  </div>
                )}

                {/* Archive Data Availability Audit Chips (Strict Rule 1, 16, 20 Compliance) */}
                <div className="env-audit-chips-container">
                  <div className="env-audit-header">ATMOSPHERIC ARCHIVE AVAILABILITY AUDIT</div>
                  <div className="env-chips-row">
                    <span className="env-available-chip" title="Full 11-member grid verified across all 6 cases">
                      ✓ MSLP FIELD: AVAILABLE
                    </span>
                    <span className="env-locked-chip" title="Absent from local single-level TIGGE archive">
                      🔒 850-hPa WIND: UNAVAILABLE
                    </span>
                    <span className="env-locked-chip" title="Absent from local single-level TIGGE archive">
                      🔒 200-hPa WIND: UNAVAILABLE
                    </span>
                    <span className="env-locked-chip" title="Cannot derive without isobaric wind levels">
                      🔒 DEEP-LAYER SHEAR: UNAVAILABLE
                    </span>
                    <span className="env-locked-chip" title="Absent from local single-level TIGGE archive">
                      🔒 700-500hPa RH: UNAVAILABLE
                    </span>
                    <span className="env-locked-chip" title="Absent from local single-level TIGGE archive">
                      🔒 SST: UNAVAILABLE
                    </span>
                  </div>
                  <div className="env-audit-disclaimer">
                    ⚠ <strong>MEASURED:</strong> NCMRWF NEPS MSLP-derived pressure-gradient geometry. <strong>UNAVAILABLE:</strong> Deep-layer shear, upper-air winds, humidity, SST (100% missingness). Surface pressure conditioning is NOT a direct measurement of vertical wind shear and is designated <strong>EXPERIMENTAL</strong> per AGENTS.md Rule 11.
                  </div>
                </div>
              </div>

              {/* OPERATIONAL QUESTION 6: HAVE SIMILAR FORECAST STATES BEEN SEEN? (HISTORICAL ANALOGUES) */}
              <div className="op-question-section highlight-historical">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q6</span>
                    <span className="op-question-title">HAVE SIMILAR FORECAST STATES BEEN SEEN?</span>
                  </div>
                  {histIntel?.top_analogue ? (
                    <span className="badge-historical">
                      {histIntel.top_analogue.similarity_percent}% MATCH
                    </span>
                  ) : (
                    <span className="badge-historical" style={{ opacity: 0.6 }}>
                      INSUFFICIENT EVIDENCE
                    </span>
                  )}
                </div>

                {histIntel?.top_analogue ? (
                  <div className="analogue-summary-card">
                    <div className="analogue-top-row">
                      <span className="analogue-name">
                        {histIntel.top_analogue.storm_name} ({histIntel.top_analogue.cycle_label}, +{histIntel.top_analogue.forecast_lead_hours}h)
                      </span>
                      <span className="analogue-sim-tag">
                        d={histIntel.top_analogue.standardized_distance.toFixed(2)}
                      </span>
                    </div>

                    <div className="telemetry-grid-2col" style={{ margin: "2px 0" }}>
                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">SIMILARITY INDEX</span>
                        <span className="telemetry-metric-value text-amber">
                          {histIntel.top_analogue.similarity_percent}%
                        </span>
                        <span className="telemetry-metric-sub">Feature distance</span>
                      </div>
                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">HISTORICAL OUTCOME</span>
                        <span className={`telemetry-metric-value ${histIntel.top_analogue.is_bust ? "text-red" : "text-green"}`}>
                          {histIntel.top_analogue.track_error_km !== null && histIntel.top_analogue.track_error_km !== undefined
                            ? `${histIntel.top_analogue.track_error_km.toFixed(1)} km`
                            : "VERIFIED"}
                        </span>
                        <span className="telemetry-metric-sub">
                          {histIntel.top_analogue.is_bust ? "⚠ Verified Bust" : "✓ Verified Nominal"}
                        </span>
                      </div>
                    </div>

                    <div className="env-narrative-note" style={{ fontSize: "9px" }}>
                      <span className="env-desc-label" style={{ color: "#eab308" }}>Pattern Match:</span>
                      {histIntel.top_analogue.failure_summary || histIntel.analogue_summary_text}
                    </div>

                    <div style={{ fontSize: "8px", color: "#64748b", fontStyle: "italic", lineHeight: 1.3 }}>
                      ℹ {histIntel.disclaimer}
                    </div>

                    <button
                      className="view-subview-link-btn"
                      onClick={() => onInvestigateView("analogues")}
                      title="Inspect 101-record historical memory and Bust Atlas"
                    >
                      Inspect Historical Analogues & Atlas →
                    </button>
                  </div>
                ) : (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>Historical forecast memory search unavailable for this prospective domain state.</span>
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 7: HOW WELL REPRESENTED IS THIS FORECAST STATE? (NOVELTY & ABSTENTION) */}
              <div className="op-question-section highlight-novelty">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q7</span>
                    <span className="op-question-title">HOW WELL REPRESENTED IS THIS FORECAST STATE?</span>
                  </div>
                  {repIntel && (
                    <span className={`badge-novelty ${repIntel.representation_state.toLowerCase()}`}>
                      {repIntel.representation_state.replace(/_/g, " ")}
                    </span>
                  )}
                </div>

                {repIntel ? (
                  <>
                    <div className="telemetry-grid-2col">
                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">SUPPORT SCORE</span>
                        <span className={`telemetry-metric-value ${repIntel.support_score > 60 ? "text-green" : repIntel.support_score > 30 ? "text-amber" : "text-orange"}`}>
                          {repIntel.support_score} / 100
                        </span>
                        <span className="telemetry-metric-sub">Reference density index</span>
                      </div>
                      <div className="telemetry-metric-cell">
                        <span className="telemetry-metric-title">REFERENCE DISTANCE</span>
                        <span className="telemetry-metric-value text-cyan">
                          {repIntel.distance_to_reference !== null && repIntel.distance_to_reference !== undefined
                            ? repIntel.distance_to_reference.toFixed(2)
                            : "N/A"}
                        </span>
                        <span className="telemetry-metric-sub">k=3 standardized d</span>
                      </div>
                    </div>

                    <div className="support-gauge-wrap">
                      <div className="support-gauge-bar">
                        <div
                          className="support-gauge-fill"
                          style={{
                            width: `${repIntel.support_score}%`,
                            background: repIntel.support_score > 60 ? "#55d98a" : repIntel.support_score > 30 ? "#ffd36a" : "#f97316",
                          }}
                        />
                      </div>
                    </div>

                    <div className={`support-callout-box ${repIntel.abstention_recommended ? "abstain" : "confirmed"}`}>
                      {repIntel.abstention_recommended ? (
                        <div>
                          <strong>⚠ ABSTENTION ADVISORY:</strong> {repIntel.abstention_reason || "Forecast state is sparsely supported by historical reference archive. High-confidence reliance not advised."}
                        </div>
                      ) : (
                        <div>
                          <strong>✓ WELL-REPRESENTED IN REFERENCE ARCHIVE:</strong> Forecast state lies within historical reference distribution (n={repIntel.reference_population_size} verified leads). Representation does not imply forecast correctness.
                        </div>
                      )}
                    </div>

                    <div style={{ fontSize: "8px", color: "#64748b", fontStyle: "italic", lineHeight: 1.3 }}>
                      ℹ {repIntel.decision_rule}
                    </div>

                    <button
                      className="view-subview-link-btn"
                      onClick={() => onInvestigateView("evidence")}
                      title="Inspect reference population distribution and support boundaries"
                    >
                      Inspect Reference Population & Support Matrix →
                    </button>
                  </>
                ) : (
                  <div className="insufficient-evidence-box">
                    <span className="lock-icon">🔒</span>
                    <span>OOD representation telemetry unavailable.</span>
                  </div>
                )}
              </div>

              {/* OPERATIONAL QUESTION 8: IS INDEPENDENT MODEL CONSENSUS AVAILABLE? (MULTI-MODEL NWP) */}
              <div className="op-question-section highlight-multimodel">
                <div className="op-question-header">
                  <div className="op-question-title-wrap">
                    <span className="op-question-num">Q8</span>
                    <span className="op-question-title">IS INDEPENDENT MODEL CONSENSUS AVAILABLE?</span>
                  </div>
                  <span className="badge-multimodel">
                    {multiIntel?.state.replace(/_/g, " ") || "INSUFFICIENT EVIDENCE"}
                  </span>
                </div>

                <div className="telemetry-grid-2col">
                  <div className="telemetry-metric-cell">
                    <span className="telemetry-metric-title">LOCAL ARCHIVE SYSTEMS</span>
                    <span className="telemetry-metric-value text-amber">
                      {multiIntel?.available_model_count || 1} / 4
                    </span>
                    <span className="telemetry-metric-sub">NCMRWF NEPS (origin=dems)</span>
                  </div>
                  <div className="telemetry-metric-cell">
                    <span className="telemetry-metric-title">CROSS-CENTER CONSENSUS</span>
                    <span className="telemetry-metric-value text-muted" style={{ color: "#94a3b8" }}>
                      UNAVAILABLE
                    </span>
                    <span className="telemetry-metric-sub">Requires ≥2 NWP centers</span>
                  </div>
                </div>

                <div className="env-narrative-note" style={{ borderLeft: "3px solid #6366f1" }}>
                  <span className="env-desc-label" style={{ color: "#a5b4fc" }}>Data Reality:</span>
                  {multiIntel?.notice || "NCMRWF NEPS is the sole operational NWP system in the validated local archive. Secondary global models (ECMWF, UKMO, NCEP) have zero historical overlap."}
                </div>

                <div style={{ fontSize: "8px", color: "#64748b", fontStyle: "italic", lineHeight: 1.3 }}>
                  Rule 1 & 12 Non-Negotiable: ForecastGuard strictly refuses to fabricate synthetic consensus from absent global NWP archives.
                </div>

                <button
                  className="view-subview-link-btn"
                  onClick={() => onInvestigateView("multimodel")}
                  title="Inspect cross-center NWP catalog and data availability audit"
                >
                  Inspect Multi-Model NWP Audit & Ingest Registry →
                </button>
              </div>

              {/* Ground Truth Verification Section (Phase 8) */}
              {selectedAssessment.verification_detail && (
                <div className="rail-section verification-foundation-section">
                  <div className="section-title-row">
                    <span className="section-title">GROUND TRUTH VERIFICATION</span>
                    <span className={`verification-badge ${selectedAssessment.verification_detail.is_bust ? "badge-bust" : "badge-nominal"}`}>
                      {selectedAssessment.verification_detail.is_bust ? "VERIFIED BUST" : "VERIFIED NOMINAL"}
                    </span>
                  </div>
                  <div className="verification-card">
                    <div className="verif-row">
                      <span className="verif-label">Valid Verification Time</span>
                      <span className="verif-val monospace-sm">{selectedAssessment.verification_detail.valid_time}</span>
                    </div>
                    <div className="verif-grid-cols">
                      <div className="verif-col">
                        <span className="verif-col-title">FORECAST FIX</span>
                        <span className="verif-coord">
                          {selectedAssessment.verification_detail.forecast_lat.toFixed(1)}°N, {selectedAssessment.verification_detail.forecast_lon.toFixed(1)}°E
                        </span>
                        <span className="verif-pressure">{selectedAssessment.verification_detail.forecast_pressure_hpa.toFixed(1)} hPa</span>
                      </div>
                      <div className="verif-col">
                        <span className="verif-col-title">IMD BEST TRACK FIX</span>
                        <span className="verif-coord text-accent">
                          {selectedAssessment.verification_detail.observed_lat.toFixed(1)}°N, {selectedAssessment.verification_detail.observed_lon.toFixed(1)}°E
                        </span>
                        <span className="verif-pressure text-accent">{selectedAssessment.verification_detail.observed_pressure_hpa.toFixed(1)} hPa</span>
                      </div>
                    </div>
                    <div className="verif-error-bar">
                      <div className="verif-error-item">
                        <span className="verif-err-label">Track Error</span>
                        <span className={`verif-err-val ${selectedAssessment.verification_detail.is_bust ? "text-red" : "text-green"}`}>
                          {selectedAssessment.verification_detail.track_error_km.toFixed(1)} km
                        </span>
                      </div>
                      <div className="verif-error-item">
                        <span className="verif-err-label">Threshold</span>
                        <span className="verif-err-val">{selectedAssessment.verification_detail.threshold_km.toFixed(1)} km</span>
                      </div>
                      <div className="verif-error-item">
                        <span className="verif-err-label">Pressure Error</span>
                        <span className="verif-err-val">{selectedAssessment.verification_detail.pressure_error_hpa.toFixed(1)} hPa</span>
                      </div>
                    </div>
                    <div className="verif-provenance-bar">
                      <span>{selectedAssessment.verification_detail.provenance}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Explicit Regional Features Section (Priority 3) */}
              {selectedAssessment.regional_features && selectedAssessment.regional_features.length > 0 && (
                <div className="rail-section features-section">
                  <div className="section-title-row">
                    <span className="section-title">REGIONAL FEATURES (V2)</span>
                    <span className="evidence-status-pill">5 AUDITED FEATURES</span>
                  </div>
                  <div className="feature-table">
                    {selectedAssessment.regional_features.map((feat) => (
                      <div key={feat.feature_name} className="feature-row">
                        <div className="feature-top-row">
                          <span className="feature-name-label">{feat.feature_name}</span>
                          <span className="feature-val-tag">
                            {feat.current_value !== null && feat.current_value !== undefined
                              ? `${feat.current_value} ${feat.units}`
                              : "N/A"}
                          </span>
                        </div>
                        <p className="feature-role-text">{feat.model_role}</p>
                        <div className="feature-meta-bar">
                          <span className="feature-source-tag">{feat.source}</span>
                          {feat.is_validated && (
                            <span className="feature-validated-tag">✓ Audited Metric</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Provenance & Audit Metadata */}
              <div className="rail-section provenance-section">
                <span className="section-title">PROVENANCE & AUDIT</span>
                <dl className="provenance-grid">
                  <div className="prov-item">
                    <dt>NWP Origin</dt>
                    <dd>{selectedAssessment.provenance.forecast_source}</dd>
                  </div>
                  <div className="prov-item">
                    <dt>Members</dt>
                    <dd>{selectedAssessment.provenance.ensemble_member_count} NEPS Perturbations</dd>
                  </div>
                  <div className="prov-item">
                    <dt>Regional Cells</dt>
                    <dd>{selectedAssessment.provenance.grid_cells_in_region.toLocaleString()} grid points</dd>
                  </div>
                  <div className="prov-item">
                    <dt>Model Version</dt>
                    <dd>{selectedAssessment.provenance.model_name} (v{selectedAssessment.provenance.model_version})</dd>
                  </div>
                  <div className="prov-item">
                    <dt>Feature Schema</dt>
                    <dd>v{selectedAssessment.provenance.feature_version}</dd>
                  </div>
                  <div className="prov-item">
                    <dt>Verification Status</dt>
                    <dd>{selectedAssessment.verification_status}</dd>
                  </div>
                  <div className="prov-item full-width">
                    <dt>Prediction Cutoff</dt>
                    <dd className="monospace-sm">{selectedAssessment.provenance.prediction_cutoff}</dd>
                  </div>
                </dl>
              </div>

              {/* Investigation Deep Dive CTA */}
              <div className="rail-action-row">
                <button
                  className="btn-investigate"
                  onClick={() => onInvestigateView("ensemble")}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  DEEP ENSEMBLE & TRAJECTORY INVESTIGATION →
                </button>
              </div>
            </div>
          ) : (
            <div className="rail-empty-state">
              <span>Select a region on the map to inspect intelligence telemetry.</span>
            </div>
          )}
          </aside>
        </div>
      </>
      )}
    </div>
  );
};
