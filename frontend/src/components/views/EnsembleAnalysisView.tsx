import React from "react";
import { DashboardState, CycloneLeadRecord } from "../../types/dashboard";

interface EnsembleAnalysisViewProps {
  state: DashboardState;
  onSelectLead: (lead: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const EnsembleAnalysisView: React.FC<EnsembleAnalysisViewProps> = ({
  state,
  onSelectLead,
  onNavigateTab,
}) => {
  const leads = state.leadsData || [];
  const activeRecord: CycloneLeadRecord | undefined =
    leads.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || leads[0];

  // Helper deterministic classifiers matching scientific/features/ contracts
  const getEnsembleState = (r?: CycloneLeadRecord) => {
    if (!r) return "INSUFFICIENT_EVIDENCE";
    const spread = r.ensemble_spread_km;
    const thresh = r.threshold_km;
    const bc = r.bimodality_coefficient;
    const sep = r.cluster_separation_km;

    if (bc >= 0.555 || sep >= 1.75 * spread) return "MULTI_BRANCH";
    if (spread > 1.5 * thresh) return "FRAGMENTED";
    if (spread > thresh) return "SPREADING";
    return "COHERENT";
  };

  const getTrajectoryState = (r?: CycloneLeadRecord) => {
    if (!r) return "INSUFFICIENT_EVIDENCE";
    const rev = r.cycle_revision_distance_km ?? 0;
    const shift = r.cycle_spread_shift_km ?? 0;
    const jitter = r.trajectory_instability_km ?? 0;

    if (rev > 75 || shift > 35) return "RAPID_REVISION";
    if (jitter > 35) return "OSCILLATING_JUMPY";
    if (rev > 30 || shift > 15) return "PROGRESSIVE_DRIFT";
    return "STABLE_PERSISTENT";
  };

  const ensembleState = getEnsembleState(activeRecord);
  const trajectoryState = getTrajectoryState(activeRecord);

  // Structured narrative derivation
  const getWhyNowNarrative = (r?: CycloneLeadRecord) => {
    if (!r) return "Insufficient telemetry to evaluate forecast breakdown.";
    if (r.bimodality_coefficient >= 0.555) {
      return `Severe track bifurcation detected in 11-member NEPS ensemble (Sarle's BC = ${r.bimodality_coefficient.toFixed(3)} ≥ 0.555). Distinct physical branches indicate competing environmental steering flow.`;
    }
    if (r.cycle_revision_distance_km && r.cycle_revision_distance_km > 60) {
      return `Consecutive cycle run jump of ${r.cycle_revision_distance_km.toFixed(1)} km at identical valid time indicates numerical instability and rapid forecast revision.`;
    }
    if (r.ensemble_spread_km > r.threshold_km) {
      return `Ensemble dispersion (${r.ensemble_spread_km.toFixed(1)} km) exceeds operational tolerance (τ = ${r.threshold_km.toFixed(1)} km), producing an expanding failure risk envelope.`;
    }
    return `Ensemble members exhibit coherent grouping (${r.ensemble_spread_km.toFixed(1)} km spread ≤ τ = ${r.threshold_km.toFixed(1)} km). Prospective reliability remains within nominal limits.`;
  };

  const getWhatChangedNarrative = (r?: CycloneLeadRecord) => {
    if (!r) return "Prior cycle lineage unavailable.";
    if (r.cycle_revision_distance_km !== null && r.cycle_revision_distance_km !== undefined) {
      const shiftStr = r.cycle_spread_shift_km !== null ? `with spread shifting ${r.cycle_spread_shift_km > 0 ? "+" : ""}${r.cycle_spread_shift_km.toFixed(1)} km` : "";
      return `Successive model issuance shifted valid vortex position by ${r.cycle_revision_distance_km.toFixed(1)} km ${shiftStr}.`;
    }
    return "Initial run initialization without prior cycle revision.";
  };

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="panel-title-group">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D", margin: 0 }}>
              ENSEMBLE & TRAJECTORY INTELLIGENCE (NCMRWF NEPS 11 MEMBERS)
            </h2>
            <span style={{ fontSize: "10px", background: "rgba(245, 184, 61, 0.15)", color: "#F5B83D", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
              {state.activeStormName || "CYCLONE"} ({state.activeCycleLabel || "00Z"})
            </span>
            <span style={{ fontSize: "10px", background: "#172335", color: "#94a3b8", padding: "2px 8px", borderRadius: "4px", fontFamily: "monospace" }}>
              LEAD {state.selectedLead}
            </span>
          </div>
          <span className="panel-subtitle">
            Physical dispersion diagnostics, cycle revision lineage, spatial anisotropy, and deterministic state classification
          </span>
        </div>
        <button
          className="btn-icon"
          style={{ width: "auto", padding: "6px 14px", fontSize: "11px", fontWeight: 600, background: "#172335", color: "#F5B83D", border: "1px solid rgba(245, 184, 61, 0.3)", borderRadius: "6px", cursor: "pointer" }}
          onClick={() => onNavigateTab("dashboard")}
        >
          ← Return to Command Center
        </button>
      </div>

      {/* Scientific Principle Callout */}
      <div
        style={{
          background: "rgba(245, 184, 61, 0.08)",
          borderLeft: "3px solid #F5B83D",
          padding: "12px 16px",
          borderRadius: "0 6px 6px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.5,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#FFD36A" }}>Operational Rule:</strong> Spread measures spatial dispersion among ensemble members. Larger spread indicates uncertainty, <em>not verified forecast error</em>. In bifurcation regimes (bimodality BC &ge; 0.555), deterministic mean tracks become dynamically unrepresentative, requiring dual-branch tracking.
      </div>

      {/* 4 Operational Questions Cockpit */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px", marginBottom: "20px" }}>
        {/* Q1: Why is reliability degrading? */}
        <div className="op-question-section highlight-degrade" style={{ background: "#0d141e", border: "1px solid rgba(180, 210, 225, 0.09)", borderLeft: "3px solid #f97316", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="op-question-num" style={{ fontSize: "8.5px", fontWeight: 800, color: "#f5b83d", background: "rgba(245, 184, 61, 0.12)", padding: "1px 5px", borderRadius: "3px" }}>Q1</span>
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#e2e8f0" }}>WHY IS RELIABILITY DEGRADING?</span>
            </div>
            <div style={{ display: "flex", gap: "4px" }}>
              <span className={`badge-ensemble ${ensembleState.toLowerCase()}`}>
                ENS: {ensembleState.replace(/_/g, " ")}
              </span>
              <span className={`badge-trajectory ${trajectoryState.toLowerCase()}`}>
                TRAJ: {trajectoryState.replace(/_/g, " ")}
              </span>
            </div>
          </div>
          <div style={{ fontSize: "11px", color: "#cbd5e1", lineHeight: 1.45, background: "#090e15", padding: "8px 10px", borderRadius: "6px" }}>
            {getWhyNowNarrative(activeRecord)}
          </div>
        </div>

        {/* Q2: What changed? */}
        <div className="op-question-section highlight-what-changed" style={{ background: "#0d141e", border: "1px solid rgba(180, 210, 225, 0.09)", borderLeft: "3px solid #f5b83d", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="op-question-num" style={{ fontSize: "8.5px", fontWeight: 800, color: "#f5b83d", background: "rgba(245, 184, 61, 0.12)", padding: "1px 5px", borderRadius: "3px" }}>Q2</span>
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#e2e8f0" }}>WHAT CHANGED ACROSS CYCLES?</span>
            </div>
            <span style={{ fontSize: "9px", fontFamily: "monospace", color: "#ffd36a", fontWeight: 700 }}>
              Δdist: {activeRecord?.cycle_revision_distance_km ? `${activeRecord.cycle_revision_distance_km.toFixed(1)} km` : "N/A"}
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "#cbd5e1", lineHeight: 1.45, background: "#090e15", padding: "8px 10px", borderRadius: "6px" }}>
            {getWhatChangedNarrative(activeRecord)}
          </div>
        </div>

        {/* Q3: How coherent is the ensemble? */}
        <div className="op-question-section highlight-ensemble" style={{ background: "#0d141e", border: "1px solid rgba(180, 210, 225, 0.09)", borderLeft: "3px solid #38bdf8", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="op-question-num" style={{ fontSize: "8.5px", fontWeight: 800, color: "#f5b83d", background: "rgba(245, 184, 61, 0.12)", padding: "1px 5px", borderRadius: "3px" }}>Q3</span>
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#e2e8f0" }}>HOW COHERENT IS THE ENSEMBLE?</span>
            </div>
            <span style={{ fontSize: "9px", color: "#38bdf8", fontWeight: 700, fontFamily: "monospace" }}>
              A={activeRecord?.anisotropy_ratio.toFixed(2) ?? "1.00"} | BC={activeRecord?.bimodality_coefficient.toFixed(3) ?? "0.33"}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
            <div style={{ background: "#090e15", padding: "6px 8px", borderRadius: "5px" }}>
              <div style={{ fontSize: "8px", color: "#64748b", fontWeight: 700 }}>CLUSTER SEPARATION</div>
              <div style={{ fontSize: "12px", color: "#f8fafc", fontWeight: 800, fontFamily: "monospace" }}>
                {activeRecord?.cluster_separation_km ? `${activeRecord.cluster_separation_km.toFixed(1)} km` : "N/A"}
              </div>
            </div>
            <div style={{ background: "#090e15", padding: "6px 8px", borderRadius: "5px" }}>
              <div style={{ fontSize: "8px", color: "#64748b", fontWeight: 700 }}>DOMINANT CLUSTER</div>
              <div style={{ fontSize: "12px", color: "#4ade80", fontWeight: 800, fontFamily: "monospace" }}>
                {activeRecord?.dominant_cluster_fraction ? `${Math.round(activeRecord.dominant_cluster_fraction * 100)}%` : "100%"}
              </div>
            </div>
          </div>
        </div>

        {/* Q4: Is the forecast becoming unstable? */}
        <div className="op-question-section highlight-trajectory" style={{ background: "#0d141e", border: "1px solid rgba(180, 210, 225, 0.09)", borderLeft: "3px solid #a855f7", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="op-question-num" style={{ fontSize: "8.5px", fontWeight: 800, color: "#f5b83d", background: "rgba(245, 184, 61, 0.12)", padding: "1px 5px", borderRadius: "3px" }}>Q4</span>
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#e2e8f0" }}>IS FORECAST BECOMING UNSTABLE?</span>
            </div>
            <span className={`badge-trajectory ${trajectoryState.toLowerCase()}`}>
              {trajectoryState.replace(/_/g, " ")}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
            <div style={{ background: "#090e15", padding: "6px 8px", borderRadius: "5px" }}>
              <div style={{ fontSize: "8px", color: "#64748b", fontWeight: 700 }}>PROPAGATION SPEED</div>
              <div style={{ fontSize: "12px", color: "#f8fafc", fontWeight: 800, fontFamily: "monospace" }}>
                {activeRecord?.trajectory_speed_kmh ? `${activeRecord.trajectory_speed_kmh.toFixed(1)} km/h` : "N/A"}
              </div>
            </div>
            <div style={{ background: "#090e15", padding: "6px 8px", borderRadius: "5px" }}>
              <div style={{ fontSize: "8px", color: "#64748b", fontWeight: 700 }}>PATH JITTER (VOLATILITY)</div>
              <div style={{ fontSize: "12px", color: "#fb923c", fontWeight: 800, fontFamily: "monospace" }}>
                {activeRecord?.trajectory_instability_km ? `${activeRecord.trajectory_instability_km.toFixed(1)} km` : "N/A"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Diagnostic Metrics Grid */}
      {activeRecord && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "20px" }}>
          <div className="metric-card" style={{ padding: "14px", background: "#0d141e", borderRadius: "6px", border: "1px solid rgba(180, 210, 225, 0.08)" }}>
            <span className="metric-title" style={{ fontSize: "9px", color: "#64748b", fontWeight: 700 }}>SCALAR SPREAD (M1)</span>
            <div className="metric-value-large highlight-amber" style={{ fontSize: "22px", fontWeight: 800, color: "#ffd36a", fontFamily: "monospace" }}>
              {activeRecord.ensemble_spread_km.toFixed(1)} km
            </div>
            <div className="metric-caption" style={{ fontSize: "9px", color: "#94a3b8" }}>Tolerance &tau;: {activeRecord.threshold_km.toFixed(1)} km</div>
          </div>
          <div className="metric-card" style={{ padding: "14px", background: "#0d141e", borderRadius: "6px", border: "1px solid rgba(180, 210, 225, 0.08)" }}>
            <span className="metric-title" style={{ fontSize: "9px", color: "#64748b", fontWeight: 700 }}>ANISOTROPY RATIO (M3)</span>
            <div className="metric-value-large highlight-blue" style={{ fontSize: "22px", fontWeight: 800, color: "#38bdf8", fontFamily: "monospace" }}>
              {activeRecord.anisotropy_ratio.toFixed(2)}
            </div>
            <div className="metric-caption" style={{ fontSize: "9px", color: "#94a3b8" }}>Major-to-minor axis ratio</div>
          </div>
          <div className="metric-card" style={{ padding: "14px", background: "#0d141e", borderRadius: "6px", border: "1px solid rgba(180, 210, 225, 0.08)" }}>
            <span className="metric-title" style={{ fontSize: "9px", color: "#64748b", fontWeight: 700 }}>BIMODALITY COEFF (M3)</span>
            <div className="metric-value-large highlight-muted" style={{ fontSize: "22px", fontWeight: 800, color: activeRecord.bimodality_coefficient >= 0.555 ? "#fb923c" : "#cbd5e1", fontFamily: "monospace" }}>
              {activeRecord.bimodality_coefficient.toFixed(3)}
            </div>
            <div className="metric-caption" style={{ fontSize: "9px", color: "#94a3b8" }}>
              {activeRecord.bimodality_coefficient >= 0.555 ? "⚠ Bifurcation (> 0.555)" : "Unimodal Gaussian"}
            </div>
          </div>
          <div className="metric-card" style={{ padding: "14px", background: "#0d141e", borderRadius: "6px", border: "1px solid rgba(180, 210, 225, 0.08)" }}>
            <span className="metric-title" style={{ fontSize: "9px", color: "#64748b", fontWeight: 700 }}>RCI CONTRADICTION (M5)</span>
            <div className="metric-value-large" style={{ fontSize: "22px", fontWeight: 800, fontFamily: "monospace", color: activeRecord.reliability_contradiction_index > 0.1 ? "#FF7878" : "#55D98A" }}>
              {activeRecord.reliability_contradiction_index.toFixed(3)}
            </div>
            <div className="metric-caption" style={{ fontSize: "9px", color: "#94a3b8" }}>Compact spread vs trajectory error</div>
          </div>
        </div>
      )}

      {/* Spread Evolution Curve Across Leads */}
      <div className="metric-card" style={{ padding: "16px", background: "#0d141e", borderRadius: "8px", border: "1px solid rgba(180, 210, 225, 0.08)", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "12px", fontWeight: 800, letterSpacing: "0.06em", color: "#FFFFFF", marginBottom: "4px" }}>
          ENSEMBLE SPREAD EVOLUTION BY FORECAST LEAD (+06h → +48h)
        </h3>
        <p style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "16px" }}>
          Track spread (gold bars) compared against the dynamic operational tolerance threshold &tau;(t) (dashed line):
        </p>

        <div style={{ height: "180px", display: "flex", alignItems: "flex-end", gap: "16px", padding: "10px 0", borderBottom: "1px solid rgba(255, 255, 255, 0.1)" }}>
          {leads.map((r) => {
            const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
            const isSelected = leadStr === state.selectedLead;
            const heightPercent = Math.min(100, Math.round((r.ensemble_spread_km / 180) * 100));

            return (
              <div
                key={r.forecast_lead_hours}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "pointer",
                  height: "100%",
                  justifyContent: "flex-end",
                }}
                onClick={() => onSelectLead(leadStr)}
              >
                {/* Threshold Marker */}
                <div style={{ fontSize: "9px", color: "#8E9DAE", marginBottom: "4px" }}>
                  &tau;={r.threshold_km.toFixed(0)}
                </div>

                {/* Spread Bar */}
                <div
                  style={{
                    width: "70%",
                    height: `${heightPercent}%`,
                    background: isSelected
                      ? "linear-gradient(180deg, #FFD36A 0%, #F5B83D 100%)"
                      : "rgba(245, 184, 61, 0.4)",
                    borderRadius: "3px 3px 0 0",
                    border: isSelected ? "1px solid #FFFFFF" : "1px solid rgba(245, 184, 61, 0.5)",
                    transition: "all 0.2s ease",
                    position: "relative",
                  }}
                  title={`Lead ${leadStr}: Spread ${r.ensemble_spread_km.toFixed(1)} km`}
                >
                  <span
                    style={{
                      position: "absolute",
                      top: "-18px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      fontSize: "9.5px",
                      color: isSelected ? "#FFD36A" : "#FFFFFF",
                      fontWeight: 700,
                    }}
                  >
                    {r.ensemble_spread_km.toFixed(0)}
                  </span>
                </div>

                {/* Label */}
                <span
                  style={{
                    fontSize: "11px",
                    marginTop: "8px",
                    fontWeight: isSelected ? 800 : 500,
                    color: isSelected ? "#F5B83D" : "#A8B2BD",
                  }}
                >
                  {leadStr}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Member Details Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
              <th style={{ padding: "8px 10px" }}>LEAD</th>
              <th style={{ padding: "8px 10px" }}>ENS STATE</th>
              <th style={{ padding: "8px 10px" }}>TRAJ STATE</th>
              <th style={{ padding: "8px 10px" }}>SPREAD</th>
              <th style={{ padding: "8px 10px" }}>&tau; THRESHOLD</th>
              <th style={{ padding: "8px 10px" }}>ANISOTROPY</th>
              <th style={{ padding: "8px 10px" }}>BIMODALITY</th>
              <th style={{ padding: "8px 10px" }}>REVISION DIST</th>
              <th style={{ padding: "8px 10px" }}>RCI</th>
              <th style={{ padding: "8px 10px" }}>EVALUATION</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((r) => {
              const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
              const isSelected = leadStr === state.selectedLead;
              const ensSt = getEnsembleState(r);
              const trajSt = getTrajectoryState(r);

              return (
                <tr
                  key={r.forecast_lead_hours}
                  style={{
                    background: isSelected ? "rgba(245, 184, 61, 0.1)" : "transparent",
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    cursor: "pointer",
                  }}
                  onClick={() => onSelectLead(leadStr)}
                >
                  <td style={{ padding: "8px 10px", fontWeight: 700, color: isSelected ? "#F5B83D" : "#FFFFFF" }}>{leadStr}</td>
                  <td style={{ padding: "8px 10px" }}>
                    <span className={`badge-ensemble ${ensSt.toLowerCase()}`} style={{ fontSize: "7.5px" }}>
                      {ensSt.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <span className={`badge-trajectory ${trajSt.toLowerCase()}`} style={{ fontSize: "7.5px" }}>
                      {trajSt.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td style={{ padding: "8px 10px", color: "#FFD36A", fontWeight: 600 }}>{r.ensemble_spread_km.toFixed(1)} km</td>
                  <td style={{ padding: "8px 10px", color: "#A8B2BD" }}>{r.threshold_km.toFixed(1)} km</td>
                  <td style={{ padding: "8px 10px", color: "#45B7D1" }}>{r.anisotropy_ratio.toFixed(2)}</td>
                  <td style={{ padding: "8px 10px", color: r.bimodality_coefficient >= 0.555 ? "#fb923c" : "#8E9DAE", fontWeight: r.bimodality_coefficient >= 0.555 ? 700 : 400 }}>
                    {r.bimodality_coefficient.toFixed(3)}
                  </td>
                  <td style={{ padding: "8px 10px", color: "#ffd36a" }}>
                    {r.cycle_revision_distance_km ? `${r.cycle_revision_distance_km.toFixed(1)} km` : "—"}
                  </td>
                  <td style={{ padding: "8px 10px", fontWeight: 600, color: r.reliability_contradiction_index > 0.1 ? "#EF4444" : "#55D98A" }}>
                    {r.reliability_contradiction_index.toFixed(3)}
                  </td>
                  <td style={{ padding: "8px 10px", color: "#A8B2BD" }}>
                    {r.bimodality_coefficient >= 0.555
                      ? "Track bifurcation (dual steering regimes)"
                      : r.ensemble_spread_km > r.threshold_km
                      ? "Diffuse member disagreement"
                      : r.anisotropy_ratio > 2.0
                      ? "Along-track elongation"
                      : "Coherent grouping"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

