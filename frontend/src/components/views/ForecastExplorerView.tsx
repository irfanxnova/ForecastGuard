import React from "react";
import { DashboardState } from "../../types/dashboard";

interface ForecastExplorerViewProps {
  state: DashboardState;
  onSelectLead: (lead: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const ForecastExplorerView: React.FC<ForecastExplorerViewProps> = ({
  state,
  onSelectLead,
  onNavigateTab,
}) => {
  const activeRecord =
    state.leadsData?.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) ||
    state.leadsData?.[0];

  const leads = state.leadsData || [];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            FORECAST EXPLORER — STEP-BY-STEP SYNOPTIC INSPECTION
          </h2>
          <span className="panel-subtitle">
            Detailed forecast lead timeline, ensemble member clustering, and threshold tolerance envelope
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

      {/* Lead Selector Bar */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "20px", background: "rgba(10, 16, 24, 0.8)", padding: "10px 14px", borderRadius: "6px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "11px", color: "#A8B2BD", fontWeight: 600 }}>Forecast Lead:</span>
        {leads.map((r) => {
          const lStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
          const isSelected = lStr === state.selectedLead;
          return (
            <button
              key={r.forecast_lead_hours}
              style={{
                background: isSelected ? "linear-gradient(135deg, #F5B83D 0%, #D9981E 100%)" : "rgba(255, 255, 255, 0.06)",
                color: isSelected ? "#0A0E14" : "#FFFFFF",
                border: isSelected ? "1px solid #FFD36A" : "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "4px",
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: isSelected ? 800 : 500,
                cursor: "pointer",
              }}
              onClick={() => onSelectLead(lStr)}
            >
              {lStr}
            </button>
          );
        })}
      </div>

      {activeRecord && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "20px" }}>
          {/* Box 1: Synoptic Forecast Center */}
          <div className="metric-card" style={{ padding: "16px" }}>
            <span className="metric-title">PREDICTED CYCLONE CENTER</span>
            <div style={{ fontSize: "22px", fontWeight: 800, color: "#FFD36A", margin: "8px 0" }}>
              {activeRecord.forecast_lat.toFixed(2)}°N, {activeRecord.forecast_lon.toFixed(2)}°E
            </div>
            <div style={{ fontSize: "11.5px", color: "#A8B2BD" }}>
              Cycle: {activeRecord.cycle_label} · Initialization: {activeRecord.initialization_time}
            </div>
            <div style={{ fontSize: "11.5px", color: "#A8B2BD", marginTop: "4px" }}>
              Forecast Valid Time: {activeRecord.forecast_valid_time}
            </div>
          </div>

          {/* Box 2: Dispersion & Tolerance */}
          <div className="metric-card" style={{ padding: "16px" }}>
            <span className="metric-title">ENSEMBLE SPREAD & TOLERANCE</span>
            <div style={{ fontSize: "22px", fontWeight: 800, color: "#45B7D1", margin: "8px 0" }}>
              {activeRecord.ensemble_spread_km.toFixed(1)} km
            </div>
            <div style={{ fontSize: "11.5px", color: "#A8B2BD" }}>
              Operational Tolerance Threshold: <strong style={{ color: "#FFFFFF" }}>{activeRecord.threshold_km.toFixed(1)} km</strong>
            </div>
            <div style={{ fontSize: "11.5px", color: "#A8B2BD", marginTop: "4px" }}>
              Spread-to-Threshold Ratio: {(activeRecord.ensemble_spread_km / activeRecord.threshold_km).toFixed(2)}
            </div>
          </div>

          {/* Box 3: Geometric Diagnostics */}
          <div className="metric-card" style={{ padding: "16px" }}>
            <span className="metric-title">GEOMETRIC SHAPE DIAGNOSTICS</span>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "8px" }}>
              <div>
                <div style={{ fontSize: "10px", color: "#8E9DAE" }}>ANISOTROPY RATIO</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
                  {activeRecord.anisotropy_ratio.toFixed(2)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "10px", color: "#8E9DAE" }}>BIMODALITY COEFF</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
                  {activeRecord.bimodality_coefficient.toFixed(4)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "10px", color: "#8E9DAE" }}>RCI INDEX (M5)</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: activeRecord.reliability_contradiction_index > 0.1 ? "#F5B83D" : "#55D98A" }}>
                  {activeRecord.reliability_contradiction_index.toFixed(3)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "10px", color: "#8E9DAE" }}>SEVERITY STATUS</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: activeRecord.severity === "SEVERE" ? "#EF4444" : "#FFD36A" }}>
                  {activeRecord.severity}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 11 Ensemble Members Clustering Visualization */}
      <div className="metric-card" style={{ padding: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          NEPS 11-MEMBER POSITION SPREAD AT {state.selectedLead}
        </h3>
        <p style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "16px" }}>
          Synthetic dispersion offsets for the 11 perturbed ensemble members around the forecast ensemble mean track center:
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: "10px" }}>
          {Array.from({ length: 11 }).map((_, idx) => {
            const spread = activeRecord?.ensemble_spread_km || 60;
            const offsetLat = ((idx - 5) * (spread / 111) * 0.4).toFixed(2);
            const offsetLon = (((idx % 3) - 1) * (spread / 111) * 0.5).toFixed(2);
            const memLat = ((activeRecord?.forecast_lat || 18.5) + parseFloat(offsetLat)).toFixed(2);
            const memLon = ((activeRecord?.forecast_lon || 87.1) + parseFloat(offsetLon)).toFixed(2);
            return (
              <div
                key={idx}
                style={{
                  background: "rgba(10, 16, 24, 0.7)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "4px",
                  padding: "8px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "10px", color: "#8E9DAE", fontWeight: 700 }}>MEMBER #{String(idx + 1).padStart(2, "0")}</div>
                <div style={{ fontSize: "11px", color: "#FFD36A", fontFamily: "monospace", margin: "4px 0" }}>
                  {memLat}°N, {memLon}°E
                </div>
                <div style={{ fontSize: "9px", color: "#55D98A" }}>Perturbed Fix</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
