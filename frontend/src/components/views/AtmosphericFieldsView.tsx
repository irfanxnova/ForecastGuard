import React from "react";
import { DashboardState } from "../../types/dashboard";

interface AtmosphericFieldsViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const AtmosphericFieldsView: React.FC<AtmosphericFieldsViewProps> = ({
  state,
  onNavigateTab,
}) => {
  const stormName = state.activeStormName || "MIDHILI";
  const activeRecord = state.leadsData?.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || state.leadsData?.[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
            </svg>
            ATMOSPHERIC FIELDS & SYNOPTIC STEERING CONTEXT
          </h2>
          <span className="panel-subtitle">
            500-hPa geopotential height analysis, environmental steering flow, and subtropical ridge orientation
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

      {/* Non-Causal Scientific Disclaimer */}
      <div
        style={{
          background: "rgba(69, 183, 209, 0.08)",
          borderLeft: "3px solid #45B7D1",
          padding: "12px 16px",
          borderRadius: "0 4px 4px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.5,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#45B7D1" }}>Scientific Integrity Notice:</strong> Atmospheric context around the forecast cyclone describes the large-scale environmental flow at 500 hPa. <em>These fields provide observational and kinematic context; they do NOT prove or claim causal attribution for forecast failure.</em> Correlation between ridge erosion and track recurvature is documented empirically without asserting deterministic causality.
      </div>

      {/* Synoptic State Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px", marginBottom: "20px" }}>
        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">500-hPa STEERING FLOW</span>
          <div className="metric-value-large highlight-amber">
            {stormName === "MIDHILI" ? "SW → NE (28 kt)" : stormName === "MICHAUNG" ? "WNW (14 kt)" : "NW → SE (12 kt)"}
          </div>
          <div className="metric-caption">Deep tropospheric mean environmental steering vector</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">SUBTROPICAL RIDGE POSITION</span>
          <div className="metric-value-large highlight-blue">
            {stormName === "MIDHILI" ? "Axis broken at 88°E" : "East-West intact along 21°N"}
          </div>
          <div className="metric-caption">Synoptic ridge boundary governing cyclone recurvature</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">GEOPOTENTIAL HEIGHT ANOMALY</span>
          <div className="metric-value-large highlight-danger">
            {stormName === "MIDHILI" ? "-42 gpm (Trough)" : "+12 gpm (Neutral)"}
          </div>
          <div className="metric-caption">Mid-tropospheric height departure from climatological baseline</div>
        </div>
      </div>

      {/* Synoptic Steering Schematic Visualization */}
      <div className="metric-card" style={{ padding: "16px", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "8px" }}>
          SYNOPTIC FLOW PATTERN AROUND CYCLONE {stormName}
        </h3>
        <p style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "14px" }}>
          Schematic representation of 500 hPa contours, ridge orientation, and environmental flow field:
        </p>

        <div style={{ background: "#080E16", borderRadius: "6px", border: "1px solid rgba(255, 255, 255, 0.08)", overflow: "hidden" }}>
          <svg viewBox="0 0 700 260" style={{ width: "100%", height: "auto", display: "block" }}>
            <rect width="700" height="260" fill="#080E16" />

            {/* Geopotential Height Isohypses (Streamlines) */}
            <g stroke="#2B4C6F" strokeWidth="1.2" fill="none" opacity="0.6">
              <path d="M 50 40 Q 250 30 450 60 T 650 90" />
              <path d="M 50 80 Q 250 70 450 110 T 650 150" />
              <path d="M 50 130 Q 250 120 420 170 T 650 210" />
              <path d="M 50 180 Q 250 180 400 220 T 650 250" />
            </g>

            {/* Subtropical Ridge Axis (Amber Dashed Line) */}
            <g stroke="#F5B83D" strokeWidth="1.8" strokeDasharray="5 4">
              <line x1="120" y1="50" x2="380" y2="45" />
              <line x1="480" y1="70" x2="660" y2="110" />
            </g>
            <text x="240" y="38" fill="#FFD36A" fontSize="9" fontWeight="700">SUBTROPICAL RIDGE AXIS</text>

            {/* Trough Fracture / Break Zone */}
            {stormName === "MIDHILI" && (
              <g>
                <circle cx="430" cy="65" r="28" stroke="#EF4444" strokeWidth="1" strokeDasharray="3 3" fill="rgba(239, 68, 68, 0.1)" />
                <text x="430" y="108" fill="#FF6B6B" fontSize="8.5" fontWeight="600" textAnchor="middle">
                  RIDGE FRACTURE ZONE (Recurvature Gateway)
                </text>
              </g>
            )}

            {/* Cyclone Position */}
            <g transform="translate(340, 160)">
              <circle cx="0" cy="0" r="14" fill="#0A1118" stroke="#FFD36A" strokeWidth="2" />
              <path d="M -8 -8 L 8 8 M -8 8 L 8 -8" stroke="#FFD36A" strokeWidth="1.8" />
              <text x="18" y="4" fill="#FFD36A" fontSize="10" fontWeight="700">
                Cyclone {stormName} ({activeRecord ? `+${activeRecord.forecast_lead_hours}h` : "+24h"})
              </text>
              <text x="18" y="16" fill="#A8B2BD" fontSize="8.5">
                {activeRecord ? `Center: ${activeRecord.forecast_lat.toFixed(1)}°N, ${activeRecord.forecast_lon.toFixed(1)}°E` : ""}
              </text>
            </g>

            {/* Steering Flow Arrows */}
            <g stroke="#45B7D1" strokeWidth="2" fill="#45B7D1">
              <line x1="310" y1="180" x2="360" y2="135" />
              <polygon points="364,131 356,136 360,143" />
              <text x="375" y="136" fill="#45B7D1" fontSize="9" fontWeight="600">Steering Vector</text>
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
};
