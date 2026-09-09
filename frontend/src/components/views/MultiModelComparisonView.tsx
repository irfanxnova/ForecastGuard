import React from "react";
import { DashboardState } from "../../types/dashboard";

interface MultiModelComparisonViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const MultiModelComparisonView: React.FC<MultiModelComparisonViewProps> = ({
  state,
  onNavigateTab,
}) => {
  const activeRecord = state.leadsData?.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || state.leadsData?.[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            MULTI-MODEL COMPARISON & DATA AVAILABILITY
          </h2>
          <span className="panel-subtitle">
            Cross-center forecast consensus capability and operational data ingestion provenance
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

      {/* Honest Capability Disclosure Callout */}
      <div
        style={{
          background: "rgba(245, 184, 61, 0.08)",
          borderLeft: "3px solid #F5B83D",
          padding: "14px 18px",
          borderRadius: "0 6px 6px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.6,
          color: "#E2E8F0",
        }}
      >
        <h4 style={{ color: "#FFD36A", fontSize: "13px", marginBottom: "4px" }}>
          Honest Provenance & Capability Status
        </h4>
        Multi-model comparison is <strong>architecturally supported</strong> in the ForecastGuard ingestion schema. However, <em>the current deployment-verified dataset contains NCMRWF NEPS/TIGGE evidence only (origin=dems, 11 perturbed members)</em>. In accordance with our agent constitution, ForecastGuard will never fabricate hypothetical forecast values for ECMWF, NCEP, or UKMO where real historical archives have not been validated.
      </div>

      {/* Model Status Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "20px" }}>
        {/* Card 1: NCMRWF NEPS (Active) */}
        <div
          className="metric-card"
          style={{
            padding: "16px",
            border: "1px solid #55D98A",
            background: "rgba(85, 217, 138, 0.04)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>NCMRWF NEPS</span>
            <span className="badge badge-stable" style={{ fontSize: "10px" }}>ACTIVE & VERIFIED</span>
          </div>
          <div style={{ fontSize: "11px", color: "#A8B2BD", lineHeight: 1.5, marginBottom: "12px" }}>
            Real archived TIGGE ensemble forecast (origin=dems). 11 perturbed members MSLP tracked and matched against official IMD/RSMC Best Tracks.
          </div>
          <div style={{ background: "rgba(10, 16, 24, 0.7)", padding: "8px 10px", borderRadius: "4px", fontSize: "11px" }}>
            <div>Spread at {state.selectedLead}: <strong style={{ color: "#FFD36A" }}>{activeRecord?.ensemble_spread_km.toFixed(1)} km</strong></div>
            <div style={{ marginTop: "4px" }}>Verified Track Error: <strong style={{ color: "#55D98A" }}>{activeRecord?.track_error_km.toFixed(1)} km</strong></div>
          </div>
        </div>

        {/* Card 2: ECMWF ENS (Pipeline Supported) */}
        <div className="metric-card" style={{ padding: "16px", opacity: 0.8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>ECMWF IFS-ENS</span>
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.08)", color: "#A8B2BD", fontSize: "10px" }}>
              INGEST READY
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "#A8B2BD", lineHeight: 1.5, marginBottom: "12px" }}>
            Schema endpoints configured for ECMWF TIGGE origin=ecmf. Not ingested in current 101-lead frozen cyclone baseline to prevent unverified comparison.
          </div>
          <div style={{ background: "rgba(10, 16, 24, 0.7)", padding: "8px 10px", borderRadius: "4px", fontSize: "11px", color: "#8E9DAE" }}>
            <div>Ingest Status: <em>Awaiting secondary license</em></div>
            <div style={{ marginTop: "4px" }}>Values: <em>Zero synthetic data emitted</em></div>
          </div>
        </div>

        {/* Card 3: NCEP GEFS (Pipeline Supported) */}
        <div className="metric-card" style={{ padding: "16px", opacity: 0.8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>NCEP GEFS</span>
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.08)", color: "#A8B2BD", fontSize: "10px" }}>
              INGEST READY
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "#A8B2BD", lineHeight: 1.5, marginBottom: "12px" }}>
            Global Ensemble Forecast System interface defined in data ingestion layer. Retained for future post-hackathon operational scaling.
          </div>
          <div style={{ background: "rgba(10, 16, 24, 0.7)", padding: "8px 10px", borderRadius: "4px", fontSize: "11px", color: "#8E9DAE" }}>
            <div>Ingest Status: <em>Interface validated</em></div>
            <div style={{ marginTop: "4px" }}>Values: <em>Zero synthetic data emitted</em></div>
          </div>
        </div>
      </div>

      {/* Decision Gate & Alignment Specifications Panel */}
      <div
        className="panel"
        style={{
          background: "rgba(10, 16, 24, 0.6)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: "6px",
          padding: "16px 20px",
          fontSize: "11.5px",
          color: "#94A3B8",
          lineHeight: 1.6,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <h4 style={{ color: "#E2E8F0", fontSize: "13px", margin: 0 }}>
            Decision Gate & Alignment Contract
          </h4>
          <span
            style={{
              padding: "2px 8px",
              background: "rgba(245, 158, 11, 0.15)",
              color: "#F59E0B",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              borderRadius: "4px",
              fontWeight: 600,
              fontSize: "10.5px",
            }}
          >
            DECISION GATE: INSUFFICIENT EVIDENCE
          </span>
        </div>
        <p style={{ margin: "0 0 10px 0" }}>
          Under Phase 2 Decision Gate rules, multi-model consensus scoring is blocked when fewer than 2 genuinely independent,
          adequately aligned models are archived. ForecastGuard retains NCMRWF NEPS as its single operational baseline and refuses
          to fabricate synthetic comparison tracks.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginTop: "12px" }}>
          <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "10px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <strong style={{ color: "#CBD5E1" }}>Temporal Alignment:</strong>
            <div>Exact 6-hourly synoptic match (&Delta;t = 0). Asynchronous runs rejected.</div>
          </div>
          <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "10px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <strong style={{ color: "#CBD5E1" }}>Agreement Bounds:</strong>
            <div>Agreement: &le;65 km / &le;8 hPa | High Disagreement: &gt;150 km / &gt;18 hPa (Experimental).</div>
          </div>
          <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "10px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <strong style={{ color: "#CBD5E1" }}>Scientific Distinction:</strong>
            <div>Cross-model disagreement is consensus dispersion, NEVER equated with forecast error.</div>
          </div>
        </div>
      </div>
    </div>
  );
};
