import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  MediumRangeForecastAnalysisResponse,
  MultiLeadForecastInput,
  TimelineLeadPoint,
} from "../../types/timeline";
import {
  TIMELINE_PRESETS,
  PRESET_MIDHILI_MULTI_LEAD,
} from "../../data/timelinePresets";

interface MediumRangeTimelineViewProps {
  backendOnline: boolean;
  onNavigateTab?: (tab: string) => void;
}

export const MediumRangeTimelineView: React.FC<MediumRangeTimelineViewProps> = ({
  backendOnline,
  onNavigateTab,
}) => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>("midhili_d1_d5");
  const [payloadInput, setPayloadInput] = useState<MultiLeadForecastInput>(PRESET_MIDHILI_MULTI_LEAD);
  const [analysisResult, setAnalysisResult] = useState<MediumRangeForecastAnalysisResponse | null>(null);
  const [selectedLeadIndex, setSelectedLeadIndex] = useState<number>(0);
  const [activeInspectorTab, setActiveInspectorTab] = useState<"pillars" | "explanations" | "telemetry" | "members">("pillars");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showJsonModal, setShowJsonModal] = useState<boolean>(false);
  const [jsonText, setJsonText] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Execute timeline analysis via API
  const runAnalysis = useCallback(async (input: MultiLeadForecastInput) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/inference/timeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (res.ok) {
        const data: MediumRangeForecastAnalysisResponse = await res.json();
        setAnalysisResult(data);
        setSelectedLeadIndex(0);
      } else {
        const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        const message = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
        setError(`Analysis rejected: ${message}`);
      }
    } catch (err: any) {
      setError(`Network error: ${err.message || "Failed to reach inference endpoint."}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    runAnalysis(payloadInput);
  }, []);

  // Preset selector
  const handlePresetSelect = (presetId: string) => {
    setSelectedPresetId(presetId);
    const preset = TIMELINE_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setPayloadInput(preset.data);
      runAnalysis(preset.data);
    }
  };

  // Upload file handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/v1/inference/upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.timeline) {
          setAnalysisResult(data as MediumRangeForecastAnalysisResponse);
          setSelectedLeadIndex(0);
        } else {
          // Single lead returned; trigger timeline wrapping
          setError("File contained a single lead. For full timeline analysis, upload a multi-lead forecast JSON.");
        }
      } else {
        const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setError(`File rejected: ${errData.detail || "Validation failure"}`);
      }
    } catch (err: any) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleOpenJsonModal = () => {
    setJsonText(JSON.stringify(payloadInput, null, 2));
    setShowJsonModal(true);
  };

  const handleApplyJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      if (!parsed.leads || !Array.isArray(parsed.leads)) {
        setError("Invalid payload: Missing required 'leads' array.");
        return;
      }
      setPayloadInput(parsed);
      setShowJsonModal(false);
      runAnalysis(parsed);
    } catch (err: any) {
      setError(`JSON Parse Error: ${err.message}`);
    }
  };

  const selectedPoint: TimelineLeadPoint | null =
    analysisResult && analysisResult.timeline[selectedLeadIndex]
      ? analysisResult.timeline[selectedLeadIndex]
      : null;

  // Helper colors
  const getTrajectoryBadgeClass = (state: string) => {
    switch (state) {
      case "IMPROVING":
        return "badge-improving";
      case "STABLE":
        return "badge-stable";
      case "DEGRADING":
        return "badge-degrading";
      case "MIXED":
        return "badge-mixed";
      default:
        return "badge-insufficient";
    }
  };

  const getReliabilityBadgeClass = (state: string | null) => {
    switch (state) {
      case "STABLE":
        return "state-stable";
      case "WATCH":
        return "state-watch";
      case "VULNERABLE":
        return "state-vulnerable";
      case "SEVERE":
        return "state-severe";
      case "UNVALIDATED_DOMAIN":
        return "state-unvalidated";
      default:
        return "state-insufficient";
    }
  };

  const getConfidenceBadgeClass = (conf: string) => {
    switch (conf) {
      case "HIGH":
        return "conf-high";
      case "MODERATE":
        return "conf-moderate";
      case "LOW":
        return "conf-low";
      default:
        return "conf-insufficient";
    }
  };

  return (
    <div className="medium-range-timeline-view">
      {/* Header Banner */}
      <div className="view-header-row">
        <div className="header-titles">
          <div className="view-eyebrow">
            OPERATIONAL WORKFLOW &bull; D+1 TO D+10 EXTENDED HORIZONS
          </div>
          <h1 className="view-title">Medium-Range Forecast Reliability & Confidence System</h1>
          <p className="view-subtitle">
            Evaluating multi-lead forecasts across D+1 (+24h) through D+10 (+240h). Providing calibrated bust probabilities within validated empirical domains and honest abstention with multi-pillar confidence across extended horizons.
          </p>
        </div>

        <div className="header-status-controls">
          <div className={`status-pill ${backendOnline ? "online" : "offline"}`}>
            <span className="status-dot"></span>
            <span>{backendOnline ? "INFERENCE API ONLINE" : "OFFLINE / LOCAL SIM"}</span>
          </div>

          {onNavigateTab && (
            <button
              className="btn-secondary"
              onClick={() => onNavigateTab("dashboard")}
              title="Return to Command Center"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
              </svg>
              Dashboard
            </button>
          )}

          <button
            className="btn-secondary"
            onClick={handleOpenJsonModal}
            title="Inspect or edit JSON payload"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            Edit Raw JSON
          </button>

          <button
            className="btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            title="Upload forecast JSON"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload JSON
          </button>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            accept=".json"
            onChange={handleFileUpload}
          />

          <button
            className="btn-primary"
            onClick={() => runAnalysis(payloadInput)}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Re-evaluate Forecast"}
          </button>
        </div>
      </div>

      {/* Preset Selector Ribbon */}
      <div className="preset-selector-bar">
        <span className="preset-label">SCENARIO PRESETS:</span>
        <div className="preset-buttons">
          {TIMELINE_PRESETS.map((p) => (
            <button
              key={p.id}
              className={`preset-btn ${selectedPresetId === p.id ? "active" : ""}`}
              onClick={() => handlePresetSelect(p.id)}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="error-banner">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
          <button className="error-close" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Scientific Domain Gating Disclosure */}
      <div className="domain-gating-banner">
        <div className="domain-indicator validated">
          <span className="badge-tag">VALIDATED EMPIRICAL DOMAIN</span>
          <span className="domain-text">D+1 &bull; D+2 (+24h to +48h) &bull; North Indian Ocean</span>
          <span className="domain-subtext">Calibrated machine learning bust probabilities (M1 Baseline).</span>
        </div>
        <div className="domain-indicator unvalidated">
          <span className="badge-tag">UNVALIDATED EXTENDED DOMAIN</span>
          <span className="domain-text">D+3 through D+10 (+72h to +240h)</span>
          <span className="domain-subtext">Bust probabilities withheld by design. Telemetry & 5-pillar confidence reported honestly.</span>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && !analysisResult && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Extracting multi-lead synoptic features and evaluating domain support...</p>
        </div>
      )}

      {/* Main Results View */}
      {analysisResult && (
        <>
          {/* Risk Evolution Banner */}
          <div className="risk-evolution-banner">
            <div className="evolution-left">
              <div className="evolution-state-badge-row">
                <span className="evolution-title">RISK EVOLUTION TRAJECTORY:</span>
                <span className={`trajectory-badge ${getTrajectoryBadgeClass(analysisResult.risk_evolution.trajectory_state)}`}>
                  {analysisResult.risk_evolution.trajectory_state}
                </span>
                <span className="leads-count-pill">
                  {analysisResult.timeline.length} LEADS EVALUATED
                </span>
              </div>
              <p className="evolution-summary">{analysisResult.risk_evolution.summary}</p>
              <div className="evidence-basis-chips">
                <span className="basis-label">Evidence Basis:</span>
                {analysisResult.risk_evolution.evidence_basis.map((item, i) => (
                  <span key={i} className="basis-chip">{item}</span>
                ))}
              </div>
            </div>

            <div className="evolution-transitions">
              <div className="transitions-label">SEQUENTIAL LEAD DELTAS</div>
              {analysisResult.risk_evolution.lead_transitions.length === 0 ? (
                <div className="no-transitions">Single lead evaluated; sequential transitions unavailable.</div>
              ) : (
                <div className="transitions-list">
                  {analysisResult.risk_evolution.lead_transitions.map((t, idx) => (
                    <div key={idx} className="transition-pill">
                      <span className="t-from-to">{t.from_lead} &rarr; {t.to_lead}</span>
                      {t.delta_spread_km !== null && t.delta_spread_km !== undefined && (
                        <span className={`t-delta ${t.delta_spread_km > 0 ? "spread-up" : "spread-down"}`}>
                          Spread {t.delta_spread_km > 0 ? `+${t.delta_spread_km}` : t.delta_spread_km} km
                        </span>
                      )}
                      <span className="t-dir">{t.direction}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* D+1 to D+10 Interactive Timeline Ribbon */}
          <div className="timeline-section">
            <div className="section-header-row">
              <h2 className="section-heading">CHRONOLOGICAL RELIABILITY TIMELINE (D+1 &rarr; D+10)</h2>
              <span className="section-hint">Click any lead card to inspect complete 5-pillar evidence and telemetry</span>
            </div>

            <div className="timeline-cards-grid">
              {analysisResult.timeline.map((point, idx) => {
                const isSelected = idx === selectedLeadIndex;
                const isValidated = point.validation_status === "VALID" || point.validation_status === "PARTIAL";
                return (
                  <div
                    key={point.lead_hours}
                    className={`timeline-lead-card ${isSelected ? "selected" : ""} ${isValidated ? "is-validated" : "is-unvalidated"}`}
                    onClick={() => setSelectedLeadIndex(idx)}
                  >
                    <div className="card-top-row">
                      <div className="lead-tag">
                        <span className="lead-name">{point.lead_name}</span>
                        <span className="lead-hours">+{point.lead_hours}h</span>
                      </div>
                      <span className={`val-status-pill ${point.probability_status}`}>
                        {point.probability_status}
                      </span>
                    </div>

                    <div className="card-prob-section">
                      <span className="prob-label">BUST PROBABILITY</span>
                      {point.bust_probability !== null ? (
                        <div className="prob-value-row">
                          <span className="prob-percent">{Math.round(point.bust_probability * 100)}%</span>
                          <span className="prob-calibrated-tag">CALIBRATED</span>
                        </div>
                      ) : (
                        <div className="prob-value-row withheld">
                          <span className="prob-withheld-label">WITHHELD</span>
                          <span className="prob-unvalidated-tag">NOT VALIDATED</span>
                        </div>
                      )}
                    </div>

                    <div className="card-meta-row">
                      <div className="meta-col">
                        <span className="meta-label">RELIABILITY STATE</span>
                        <span className={`meta-state ${getReliabilityBadgeClass(point.reliability_state)}`}>
                          {point.reliability_state || "UNVALIDATED"}
                        </span>
                      </div>
                      <div className="meta-col text-right">
                        <span className="meta-label">CONFIDENCE</span>
                        <span className={`meta-conf ${getConfidenceBadgeClass(point.assessment_confidence)}`}>
                          {point.assessment_confidence}
                        </span>
                      </div>
                    </div>

                    <div className="card-bottom-row">
                      <span className={`data-quality-badge ${point.data_quality.replace(/\s+/g, "_")}`}>
                        {point.data_quality}
                      </span>
                      {point.support_index !== null && (
                        <span className="support-index-tag" title="Empirical dispersion support index [0-100]">
                          SUP: {point.support_index}/100
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Deep Inspector for Selected Lead */}
          {selectedPoint && (
            <div className="lead-inspector-panel">
              {/* Selected Lead Overview Header */}
              <div className="inspector-header">
                <div className="inspector-title-block">
                  <div className="inspector-lead-badge">
                    <span>{selectedPoint.lead_name}</span>
                    <span className="lead-hours-chip">+{selectedPoint.lead_hours} HOURS</span>
                  </div>
                  <div>
                    <h3 className="inspector-title">
                      Detailed Assessment for Valid Time: {new Date(selectedPoint.valid_time).toUTCString()}
                    </h3>
                    <p className="inspector-meta">
                      Initialization Cycle: {analysisResult.forecast_cycle} &bull; Center: {analysisResult.forecast_source} &bull; Model: {analysisResult.timeline[0]?.features_extracted ? "NCMRWF_NEPS" : "Multi-center"}
                    </p>
                  </div>
                </div>

                <div className="inspector-summary-stats">
                  <div className="stat-box">
                    <span className="stat-label">BUST PROBABILITY</span>
                    <span className={`stat-value ${selectedPoint.bust_probability !== null ? "has-prob" : "withheld"}`}>
                      {selectedPoint.bust_probability !== null
                        ? `${Math.round(selectedPoint.bust_probability * 100)}%`
                        : "WITHHELD"}
                    </span>
                    <span className="stat-sub">{selectedPoint.probability_status}</span>
                  </div>

                  <div className="stat-box">
                    <span className="stat-label">RELIABILITY STATE</span>
                    <span className={`stat-value ${getReliabilityBadgeClass(selectedPoint.reliability_state)}`}>
                      {selectedPoint.reliability_state || "UNVALIDATED"}
                    </span>
                    <span className="stat-sub">{selectedPoint.validation_status}</span>
                  </div>

                  <div className="stat-box">
                    <span className="stat-label">EVIDENCE CONFIDENCE</span>
                    <span className={`stat-value ${getConfidenceBadgeClass(selectedPoint.assessment_confidence)}`}>
                      {selectedPoint.assessment_confidence}
                    </span>
                    <span className="stat-sub">5-PILLAR AUDIT</span>
                  </div>
                </div>
              </div>

              {/* Inspector Sub-Navigation Tabs */}
              <div className="inspector-tabs">
                <button
                  className={`inspector-tab-btn ${activeInspectorTab === "pillars" ? "active" : ""}`}
                  onClick={() => setActiveInspectorTab("pillars")}
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <line x1="3" y1="9" x2="21" y2="9" />
                    <line x1="9" y1="21" x2="9" y2="9" />
                  </svg>
                  5-Pillar Confidence Breakdown
                </button>

                <button
                  className={`inspector-tab-btn ${activeInspectorTab === "explanations" ? "active" : ""}`}
                  onClick={() => setActiveInspectorTab("explanations")}
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                  Structured Explanations (WHY / WHAT CHANGED / WHY NOW)
                </button>

                <button
                  className={`inspector-tab-btn ${activeInspectorTab === "telemetry" ? "active" : ""}`}
                  onClick={() => setActiveInspectorTab("telemetry")}
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                  Audited Feature Telemetry
                </button>

                <button
                  className={`inspector-tab-btn ${activeInspectorTab === "members" ? "active" : ""}`}
                  onClick={() => setActiveInspectorTab("members")}
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  </svg>
                  Consensus & Multi-Model Agreement
                </button>
              </div>

              {/* Tab 1: 5-Pillars of Confidence */}
              {activeInspectorTab === "pillars" && (
                <div className="tab-pane pillars-pane">
                  <div className="pillars-grid">
                    {/* Pillar 1: Data Coverage */}
                    <div className="pillar-card">
                      <div className="pillar-header">
                        <span className="pillar-number">PILLAR 1</span>
                        <h4 className="pillar-title">Data Coverage</h4>
                        <span className={`pillar-status-badge ${selectedPoint.confidence_breakdown.data_coverage.status}`}>
                          {selectedPoint.confidence_breakdown.data_coverage.status}
                        </span>
                      </div>
                      <p className="pillar-reason">{selectedPoint.confidence_breakdown.data_coverage.reason}</p>
                      <div className="pillar-source">Source: {selectedPoint.confidence_breakdown.data_coverage.source}</div>
                    </div>

                    {/* Pillar 2: Model Validation */}
                    <div className="pillar-card">
                      <div className="pillar-header">
                        <span className="pillar-number">PILLAR 2</span>
                        <h4 className="pillar-title">Model Validation</h4>
                        <span className={`pillar-status-badge ${selectedPoint.confidence_breakdown.model_validation.status}`}>
                          {selectedPoint.confidence_breakdown.model_validation.status}
                        </span>
                      </div>
                      <p className="pillar-reason">{selectedPoint.confidence_breakdown.model_validation.reason}</p>
                      <div className="pillar-source">Source: {selectedPoint.confidence_breakdown.model_validation.source}</div>
                    </div>

                    {/* Pillar 3: Historical Representation */}
                    <div className="pillar-card">
                      <div className="pillar-header">
                        <span className="pillar-number">PILLAR 3</span>
                        <h4 className="pillar-title">Historical Representation</h4>
                        <span className={`pillar-status-badge ${selectedPoint.confidence_breakdown.historical_representation.status}`}>
                          {selectedPoint.confidence_breakdown.historical_representation.status}
                        </span>
                      </div>
                      <p className="pillar-reason">{selectedPoint.confidence_breakdown.historical_representation.reason}</p>
                      <div className="pillar-source">Source: {selectedPoint.confidence_breakdown.historical_representation.source}</div>
                    </div>

                    {/* Pillar 4: Ensemble Support */}
                    <div className="pillar-card">
                      <div className="pillar-header">
                        <span className="pillar-number">PILLAR 4</span>
                        <h4 className="pillar-title">Ensemble Support</h4>
                        <span className={`pillar-status-badge ${selectedPoint.confidence_breakdown.ensemble_support.status}`}>
                          {selectedPoint.confidence_breakdown.ensemble_support.status}
                        </span>
                      </div>
                      <p className="pillar-reason">{selectedPoint.confidence_breakdown.ensemble_support.reason}</p>
                      <div className="pillar-source">Source: {selectedPoint.confidence_breakdown.ensemble_support.source}</div>
                    </div>

                    {/* Pillar 5: Provenance */}
                    <div className="pillar-card pillar-card-full">
                      <div className="pillar-header">
                        <span className="pillar-number">PILLAR 5</span>
                        <h4 className="pillar-title">Lineage & Provenance</h4>
                        <span className={`pillar-status-badge ${selectedPoint.confidence_breakdown.provenance.status}`}>
                          {selectedPoint.confidence_breakdown.provenance.status}
                        </span>
                      </div>
                      <p className="pillar-reason">{selectedPoint.confidence_breakdown.provenance.reason}</p>
                      <div className="pillar-source">Source: {selectedPoint.confidence_breakdown.provenance.source}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Structured Explanations */}
              {activeInspectorTab === "explanations" && (
                <div className="tab-pane explanations-pane">
                  <div className="explanation-card why-card">
                    <div className="card-label-row">
                      <span className="expl-tag why-tag">WHY</span>
                      <span className="expl-subtitle">Direct empirical evidence supporting this reliability state</span>
                    </div>
                    <p className="expl-text">{selectedPoint.structured_explanation.why}</p>
                  </div>

                  <div className="explanation-card what-changed-card">
                    <div className="card-label-row">
                      <span className="expl-tag what-tag">WHAT CHANGED</span>
                      <span className="expl-subtitle">Sequential delta relative to preceding forecast lead</span>
                    </div>
                    <p className="expl-text">
                      {selectedPoint.structured_explanation.what_changed ||
                        "Baseline lead step (D+1). Preceding forecast step does not exist for delta comparison."}
                    </p>
                  </div>

                  <div className="explanation-card why-now-card">
                    <div className="card-label-row">
                      <span className="expl-tag now-tag">WHY NOW</span>
                      <span className="expl-subtitle">Current synoptic trigger and geometric dispersion status</span>
                    </div>
                    <p className="expl-text">{selectedPoint.structured_explanation.why_now}</p>
                  </div>
                </div>
              )}

              {/* Tab 3: Audited Feature Telemetry */}
              {activeInspectorTab === "telemetry" && (
                <div className="tab-pane telemetry-pane">
                  <div className="telemetry-table-wrapper">
                    <table className="telemetry-table">
                      <thead>
                        <tr>
                          <th>PHYSICAL FEATURE</th>
                          <th>VALUE</th>
                          <th>UNIT</th>
                          <th>SOURCE</th>
                          <th>AVAILABILITY</th>
                          <th>VALIDATION</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedPoint.feature_telemetry && selectedPoint.feature_telemetry.length > 0 ? (
                          selectedPoint.feature_telemetry.map((item, idx) => (
                            <tr key={idx}>
                              <td className="font-semibold">{item.name}</td>
                              <td className="font-mono text-cyan">{item.value}</td>
                              <td className="text-muted">{item.unit}</td>
                              <td className="text-secondary">{item.source}</td>
                              <td>
                                <span className={`table-badge ${item.availability}`}>
                                  {item.availability}
                                </span>
                              </td>
                              <td>
                                <span className={`table-badge ${item.validation_status}`}>
                                  {item.validation_status}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={6} className="text-center py-4 text-muted">
                              Telemetry unavailable for this forecast lead.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Tab 4: Multi-Model & Consensus */}
              {activeInspectorTab === "members" && (
                <div className="tab-pane consensus-pane">
                  <div className="consensus-layout">
                    <div className="consensus-card">
                      <h4 className="consensus-title">Cross-Model NWP Agreement</h4>
                      {selectedPoint.multimodel_evidence ? (
                        <div className="consensus-body">
                          <div className="consensus-state-row">
                            <span className="consensus-label">AGREEMENT STATE:</span>
                            <span className={`consensus-badge ${selectedPoint.multimodel_evidence.state}`}>
                              {selectedPoint.multimodel_evidence.state}
                            </span>
                          </div>
                          <p className="consensus-notice">{selectedPoint.multimodel_evidence.agreement_notice}</p>
                          <div className="consensus-meta-list">
                            <div>Models Evaluated: {selectedPoint.multimodel_evidence.models_evaluated.join(", ")}</div>
                            <div>Available Model Count: {selectedPoint.multimodel_evidence.available_model_count}</div>
                            {selectedPoint.multimodel_evidence.mean_track_separation_km !== null && (
                              <div>Mean Track Separation: {selectedPoint.multimodel_evidence.mean_track_separation_km} km</div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted">Multi-model comparison data pending or unavailable.</p>
                      )}
                    </div>

                    <div className="consensus-card">
                      <h4 className="consensus-title">Novelty & Historical Reference</h4>
                      {selectedPoint.novelty_assessment ? (
                        <div className="consensus-body">
                          <div className="consensus-state-row">
                            <span className="consensus-label">REPRESENTATION:</span>
                            <span className={`novelty-badge ${selectedPoint.novelty_assessment.representation_state}`}>
                              {selectedPoint.novelty_assessment.representation_state}
                            </span>
                          </div>
                          <p className="consensus-notice">{selectedPoint.novelty_assessment.scientific_notice}</p>
                          <div className="consensus-meta-list">
                            <div>Nearest Reference Storm: {selectedPoint.novelty_assessment.nearest_historical_case}</div>
                            <div>Novelty Distance: {selectedPoint.novelty_assessment.distance.toFixed(3)}</div>
                            <div>Reference Quantile: {(selectedPoint.novelty_assessment.quantile * 100).toFixed(1)}%</div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted">Novelty evaluation unavailable.</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Prospective Anti-Leakage Guarantee Footer */}
          <div className="prospective-audit-footer">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>
              <strong>PROSPECTIVE ANTI-LEAKAGE GUARANTEE:</strong> Ground truth verification data is strictly withheld from all inference calculations. Evaluated at {analysisResult.provenance.evaluated_at_utc} UTC against calibration baseline {analysisResult.provenance.calibration_cohort}.
            </span>
          </div>
        </>
      )}

      {/* Raw JSON Editor Modal */}
      {showJsonModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Multi-Lead Forecast Payload (JSON)</h3>
              <button className="modal-close" onClick={() => setShowJsonModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p className="modal-sub">
                Edit or paste an operational multi-lead forecast payload. Strict anti-leakage guards forbid any ground truth fields.
              </p>
              <textarea
                className="json-textarea"
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                rows={16}
              />
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowJsonModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleApplyJson}>Validate & Evaluate</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
