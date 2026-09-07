import React from "react";
import { DashboardState } from "../../types/dashboard";

interface EvidenceDataViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const EvidenceDataView: React.FC<EvidenceDataViewProps> = ({
  onNavigateTab,
}) => {
  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            EVIDENCE PROVENANCE & DATA ARCHITECTURE
          </h2>
          <span className="panel-subtitle">
            Scientific origin, official verification agencies, and strict live vs historical data isolation
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

      {/* Provenance Pillars */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#F5B83D", fontWeight: 700, textTransform: "uppercase", marginBottom: "6px" }}>
            FORECAST DATA SOURCE
          </div>
          <div style={{ fontSize: "16px", fontWeight: 800, color: "#FFFFFF", marginBottom: "6px" }}>
            NCMRWF NEPS / TIGGE
          </div>
          <div style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            Origin: <code style={{ color: "#FFD36A" }}>dems</code> (National Centre for Medium Range Weather Forecasting). 11 perturbed ensemble members initialized at 00 and 12 UTC, with 6-hourly steps (+06h to +48h).
          </div>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#45B7D1", fontWeight: 700, textTransform: "uppercase", marginBottom: "6px" }}>
            OFFICIAL GROUND TRUTH
          </div>
          <div style={{ fontSize: "16px", fontWeight: 800, color: "#FFFFFF", marginBottom: "6px" }}>
            IMD / RSMC NEW DELHI
          </div>
          <div style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            Official Regional Specialized Meteorological Centre (RSMC) New Delhi Tropical Cyclone Best Track archive (1982–2026). Continuous 6-hourly vortex center coordinates and intensity.
          </div>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#55D98A", fontWeight: 700, textTransform: "uppercase", marginBottom: "6px" }}>
            VERIFIED SCOPE
          </div>
          <div style={{ fontSize: "16px", fontWeight: 800, color: "#FFFFFF", marginBottom: "6px" }}>
            101 Synoptic Leads
          </div>
          <div style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            13 forecast cycles across 6 cyclones (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, MICHAUNG). Zero temporal interpolation or synthetic observation generation.
          </div>
        </div>
      </div>

      {/* Live vs Historical Separation Protocol */}
      <div className="metric-card" style={{ padding: "18px", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          STRICT LIVE vs HISTORICAL DATA SEPARATION PROTOCOL
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
          {/* Live Protocol */}
          <div style={{ background: "rgba(10, 16, 24, 0.7)", padding: "14px", borderRadius: "6px", border: "1px solid rgba(69, 183, 209, 0.3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <span className="badge badge-stable" style={{ background: "rgba(69, 183, 209, 0.2)", color: "#45B7D1", borderColor: "rgba(69, 183, 209, 0.4)" }}>
                LIVE INFERENCE MODE
              </span>
            </div>
            <ul style={{ fontSize: "11.5px", color: "#C5D0DC", lineHeight: 1.6, paddingLeft: "16px", margin: 0 }}>
              <li>Future observations are strictly unknown and quarantined.</li>
              <li>Model vulnerability scores are calculated solely from prospective ensemble features available at evaluation time.</li>
              <li>Verification status displays <em>"Awaiting Observation"</em>.</li>
              <li>No ground truth errors or failure claims can be asserted.</li>
            </ul>
          </div>

          {/* Historical Protocol */}
          <div style={{ background: "rgba(10, 16, 24, 0.7)", padding: "14px", borderRadius: "6px", border: "1px solid rgba(245, 184, 61, 0.3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <span className="badge badge-degrading" style={{ background: "rgba(245, 184, 61, 0.2)", color: "#FFD36A", borderColor: "rgba(245, 184, 61, 0.4)" }}>
                HISTORICAL REPLAY MODE
              </span>
            </div>
            <ul style={{ fontSize: "11.5px", color: "#C5D0DC", lineHeight: 1.6, paddingLeft: "16px", margin: 0 }}>
              <li>Ground truth IMD observation is withheld until operator clicks <code>[ Reveal Observation ]</code>.</li>
              <li>Enables retrospective verification against official best track.</li>
              <li>Enables interactive forecast-vs-reality replay animation.</li>
              <li>Generates verified failure fingerprints and error evolution profiles.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
