import React from "react";
import { DashboardState } from "../../types/dashboard";

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
  const activeRecord = leads.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || leads[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            ENSEMBLE ANALYSIS & GEOMETRY (NCMRWF NEPS 11 MEMBERS)
          </h2>
          <span className="panel-subtitle">
            Dispersion diagnostics, spread evolution, spatial anisotropy, and Reliability Contradiction Index
          </span>
        </div>
        <button
          className="btn-icon"
          style={{ width: "auto", padding: "6px 12px", fontSize: "11px", fontWeight: 600 }}
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
          borderRadius: "0 4px 4px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.5,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#FFD36A" }}>Operational Rule:</strong> Spread measures how far apart the ensemble cyclone positions are. Larger spread indicates greater forecast disagreement among members. <em>However, spread alone does not prove failure</em>: a tightly clustered ensemble can fail when environmental steering changes rapidly (a false-confidence regime), whereas an anisotropic spread may faithfully reflect cross-track uncertainty.
      </div>

      {/* Key Diagnostic Metrics for Active Lead */}
      {activeRecord && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "20px" }}>
          <div className="metric-card" style={{ padding: "14px" }}>
            <span className="metric-title">SCALAR SPREAD (M1)</span>
            <div className="metric-value-large highlight-amber">{activeRecord.ensemble_spread_km.toFixed(1)} km</div>
            <div className="metric-caption">Mean distance of members from ensemble mean</div>
          </div>
          <div className="metric-card" style={{ padding: "14px" }}>
            <span className="metric-title">ANISOTROPY RATIO (M3)</span>
            <div className="metric-value-large highlight-blue">{activeRecord.anisotropy_ratio.toFixed(2)}</div>
            <div className="metric-caption">Major-to-minor principal axis dispersion ratio</div>
          </div>
          <div className="metric-card" style={{ padding: "14px" }}>
            <span className="metric-title">BIMODALITY COEFF (M3)</span>
            <div className="metric-value-large highlight-muted">{activeRecord.bimodality_coefficient.toFixed(4)}</div>
            <div className="metric-caption">Sarle's bimodality (Values &gt; 0.555 indicate bifurcating tracks)</div>
          </div>
          <div className="metric-card" style={{ padding: "14px" }}>
            <span className="metric-title">RCI CONTRADICTION (M5)</span>
            <div className="metric-value-large" style={{ color: activeRecord.reliability_contradiction_index > 0.1 ? "#FF7878" : "#55D98A" }}>
              {activeRecord.reliability_contradiction_index.toFixed(3)}
            </div>
            <div className="metric-caption">Contradiction between spread compactness and trajectory error</div>
          </div>
        </div>
      )}

      {/* Spread Evolution Curve Across Leads */}
      <div className="metric-card" style={{ padding: "16px", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "8px" }}>
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
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
              <th style={{ padding: "8px 10px" }}>LEAD</th>
              <th style={{ padding: "8px 10px" }}>SPREAD (km)</th>
              <th style={{ padding: "8px 10px" }}>THRESHOLD &tau; (km)</th>
              <th style={{ padding: "8px 10px" }}>ANISOTROPY A</th>
              <th style={{ padding: "8px 10px" }}>BIMODALITY BC</th>
              <th style={{ padding: "8px 10px" }}>RCI INDEX</th>
              <th style={{ padding: "8px 10px" }}>INTERPRETATION</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((r) => {
              const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
              const isSelected = leadStr === state.selectedLead;
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
                  <td style={{ padding: "8px 10px", color: "#FFD36A", fontWeight: 600 }}>{r.ensemble_spread_km.toFixed(1)} km</td>
                  <td style={{ padding: "8px 10px", color: "#A8B2BD" }}>{r.threshold_km.toFixed(1)} km</td>
                  <td style={{ padding: "8px 10px", color: "#45B7D1" }}>{r.anisotropy_ratio.toFixed(2)}</td>
                  <td style={{ padding: "8px 10px", color: "#8E9DAE" }}>{r.bimodality_coefficient.toFixed(4)}</td>
                  <td style={{ padding: "8px 10px", fontWeight: 600, color: r.reliability_contradiction_index > 0.1 ? "#EF4444" : "#55D98A" }}>
                    {r.reliability_contradiction_index.toFixed(3)}
                  </td>
                  <td style={{ padding: "8px 10px", color: "#A8B2BD" }}>
                    {r.ensemble_spread_km > r.threshold_km
                      ? "High member disagreement (diffuse envelope)"
                      : r.anisotropy_ratio > 2.0
                      ? "Along-track elongation"
                      : "Coherent member grouping"}
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
