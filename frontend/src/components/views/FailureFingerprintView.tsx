import React from "react";
import { DashboardState } from "../../types/dashboard";
import { STORMS_CATALOG } from "../../data/casesData";

interface FailureFingerprintViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
  onSelectStorm?: (stormName: string) => void;
}

export const FailureFingerprintView: React.FC<FailureFingerprintViewProps> = ({
  state,
  onNavigateTab,
  onSelectStorm,
}) => {
  const stormName = state.activeStormName || "MIDHILI";
  const stormMeta = STORMS_CATALOG.find((s) => s.name === stormName) || STORMS_CATALOG[0];
  const leads = state.leadsData || [];
  const failures = leads.filter((r) => r.bust_label === 1);
  const onsetRecord = failures[0] || leads[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
            </svg>
            FAILURE FINGERPRINT — {stormName}
          </h2>
          <span className="panel-subtitle">
            Anatomy, temporal onset, and diagnostic signature of verified forecast track failure
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

      {/* Case Switcher */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "20px", background: "rgba(10, 16, 24, 0.8)", padding: "10px 14px", borderRadius: "6px" }}>
        <span style={{ fontSize: "11px", color: "#F5B83D", fontWeight: 700 }}>Inspect Storm Fingerprint:</span>
        <select
          value={stormName}
          onChange={(e) => onSelectStorm && onSelectStorm(e.target.value)}
          className="select-control"
          style={{ padding: "4px 8px", fontSize: "11px", fontWeight: 600 }}
        >
          {STORMS_CATALOG.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name} ({s.highlightTag})
            </option>
          ))}
        </select>
      </div>

      {/* Key Fingerprint Characteristics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", marginBottom: "20px" }}>
        <div className="metric-card" style={{ padding: "16px" }}>
          <span className="metric-title">FAILURE CLASSIFICATION</span>
          <div style={{ fontSize: "17px", fontWeight: 800, color: "#FFFFFF", margin: "8px 0" }}>
            {stormMeta.highlightTag}
          </div>
          <div className="metric-caption">{stormMeta.narrative}</div>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <span className="metric-title">FAILURE ONSET LEAD</span>
          <div style={{ fontSize: "22px", fontWeight: 800, color: failures.length > 0 ? "#EF4444" : "#55D98A", margin: "8px 0" }}>
            {failures.length > 0 ? `+${String(onsetRecord.forecast_lead_hours).padStart(2, "0")}h` : "No Failure Detected"}
          </div>
          <div className="metric-caption">
            {failures.length > 0
              ? `First tolerance exceedance: ${onsetRecord.track_error_km.toFixed(1)} km vs &tau; = ${onsetRecord.threshold_km.toFixed(1)} km`
              : "All forecast leads remained within operational tolerance envelope."}
          </div>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <span className="metric-title">PEAK VERIFIED ERROR</span>
          <div style={{ fontSize: "22px", fontWeight: 800, color: stormMeta.maxErrorKm > 200 ? "#EF4444" : "#F59E0B", margin: "8px 0" }}>
            {stormMeta.maxErrorKm.toFixed(1)} km
          </div>
          <div className="metric-caption">Mean track displacement across 48h: {stormMeta.meanErrorKm.toFixed(1)} km</div>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <span className="metric-title">FAILURE DURATION</span>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#FFD36A", margin: "8px 0" }}>
            {failures.length > 0 ? `${failures.length * 6} Hours` : "0 Hours"}
          </div>
          <div className="metric-caption">{failures.length} of {leads.length} verified synoptic steps breached tolerance</div>
        </div>
      </div>

      {/* Lead-by-Lead Failure Evolution Fingerprint */}
      <div className="metric-card" style={{ padding: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          TEMPORAL ERROR ESCALATION FINGERPRINT
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {leads.map((r) => {
            const isFailure = r.bust_label === 1;
            const barWidthPercent = Math.min(100, Math.round((r.track_error_km / 550) * 100));
            return (
              <div key={r.forecast_lead_hours} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ width: "40px", fontSize: "11px", fontWeight: 700, color: isFailure ? "#FF7878" : "#A8B2BD" }}>
                  +{String(r.forecast_lead_hours).padStart(2, "0")}h
                </span>
                <div style={{ flex: 1, background: "rgba(255, 255, 255, 0.05)", height: "22px", borderRadius: "3px", overflow: "hidden", position: "relative" }}>
                  <div
                    style={{
                      width: `${barWidthPercent}%`,
                      height: "100%",
                      background: r.severity === "SEVERE"
                        ? "linear-gradient(90deg, #F59E0B 0%, #EF4444 100%)"
                        : isFailure
                        ? "#F59E0B"
                        : "#55D98A",
                      borderRadius: "3px",
                      transition: "width 0.4s ease",
                    }}
                  />
                  <span
                    style={{
                      position: "absolute",
                      left: `${Math.min(92, barWidthPercent + 2)}%`,
                      top: "50%",
                      transform: "translateY(-50%)",
                      fontSize: "10.5px",
                      fontWeight: 700,
                      color: isFailure ? "#FFD36A" : "#FFFFFF",
                    }}
                  >
                    {r.track_error_km.toFixed(1)} km
                  </span>
                </div>
                <span
                  className="badge"
                  style={{
                    width: "80px",
                    textAlign: "center",
                    fontSize: "9.5px",
                    background: r.severity === "SEVERE" ? "rgba(239, 68, 68, 0.2)" : isFailure ? "rgba(245, 158, 11, 0.2)" : "rgba(85, 217, 138, 0.2)",
                    color: r.severity === "SEVERE" ? "#FF7878" : isFailure ? "#F5B83D" : "#55D98A",
                  }}
                >
                  {r.severity}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
