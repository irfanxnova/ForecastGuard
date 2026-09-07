import React, { useState } from "react";
import { DashboardState } from "../../types/dashboard";
import { BUST_ATLAS_DATA, STORMS_CATALOG } from "../../data/casesData";

interface ActiveAlertsViewProps {
  state: DashboardState;
  onSelectStorm?: (stormName: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const ActiveAlertsView: React.FC<ActiveAlertsViewProps> = ({
  state: _state,
  onSelectStorm,
  onNavigateTab,
}) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedStormFilter, setSelectedStormFilter] = useState<string>("ALL");

  const filteredAlerts = BUST_ATLAS_DATA.filter((alert: any) => {
    if (selectedSeverity !== "ALL" && alert.severity !== selectedSeverity) return false;
    if (selectedStormFilter !== "ALL" && alert.storm_name.toUpperCase() !== selectedStormFilter.toUpperCase()) return false;
    return true;
  });

  const handleInspect = (stormName: string) => {
    if (onSelectStorm) {
      onSelectStorm(stormName);
    }
    onNavigateTab("dashboard");
  };

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            ACTIVE ALERTS & VERIFIED FAILURE RECORDS
          </h2>
          <span className="panel-subtitle">
            Curated failure occurrences from the North Indian Ocean NCMRWF TIGGE verified archive
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

      {/* Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "20px" }}>
        <div className="metric-card" style={{ padding: "12px" }}>
          <span className="metric-title">TOTAL VERIFIED FAILURES</span>
          <div className="metric-value-large highlight-danger">{BUST_ATLAS_DATA.length}</div>
          <div className="metric-caption">Contemporaneous busts across 101 verified leads</div>
        </div>
        <div className="metric-card" style={{ padding: "12px" }}>
          <span className="metric-title">SEVERE TRACK DISPLACEMENTS</span>
          <div className="metric-value-large highlight-danger">
            {BUST_ATLAS_DATA.filter((a: any) => a.severity === "SEVERE").length}
          </div>
          <div className="metric-caption">Displacements exceeding 1.5x operational threshold</div>
        </div>
        <div className="metric-card" style={{ padding: "12px" }}>
          <span className="metric-title">PEAK VERIFIED ERROR</span>
          <div className="metric-value-large highlight-amber">548.5 km</div>
          <div className="metric-caption">Cyclone MIDHILI +48h (Northeast acceleration)</div>
        </div>
        <div className="metric-card" style={{ padding: "12px" }}>
          <span className="metric-title">VERIFIED STORMS</span>
          <div className="metric-value-large highlight-blue">{STORMS_CATALOG.length}</div>
          <div className="metric-caption">MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, MICHAUNG</div>
        </div>
      </div>

      {/* Filter Controls */}
      <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "16px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600 }}>Filter Storm:</span>
          <select
            value={selectedStormFilter}
            onChange={(e) => setSelectedStormFilter(e.target.value)}
            className="select-control"
            style={{ padding: "4px 8px", fontSize: "11px" }}
          >
            <option value="ALL">All Storms ({BUST_ATLAS_DATA.length})</option>
            {STORMS_CATALOG.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.bustsCount} failures)
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600 }}>Severity:</span>
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="select-control"
            style={{ padding: "4px 8px", fontSize: "11px" }}
          >
            <option value="ALL">All Severities</option>
            <option value="SEVERE">Severe</option>
            <option value="DEGRADED">Degraded</option>
            <option value="MODERATE">Moderate</option>
          </select>
        </div>

        <span style={{ fontSize: "11px", color: "#A8B2BD", marginLeft: "auto" }}>
          Showing {filteredAlerts.length} of {BUST_ATLAS_DATA.length} records
        </span>
      </div>

      {/* Alerts Table */}
      <div style={{ overflowX: "auto", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "6px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
              <th style={{ padding: "10px 12px" }}>STORM</th>
              <th style={{ padding: "10px 12px" }}>CYCLE</th>
              <th style={{ padding: "10px 12px" }}>LEAD</th>
              <th style={{ padding: "10px 12px" }}>FORECAST CENTER</th>
              <th style={{ padding: "10px 12px" }}>OBSERVED RSMC</th>
              <th style={{ padding: "10px 12px" }}>TRACK ERROR</th>
              <th style={{ padding: "10px 12px" }}>THRESHOLD</th>
              <th style={{ padding: "10px 12px" }}>SEVERITY</th>
              <th style={{ padding: "10px 12px" }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredAlerts.map((record: any, idx: number) => {
              const isSevere = record.severity === "SEVERE";
              const isDegraded = record.severity === "DEGRADED";
              return (
                <tr
                  key={`${record.storm_name}-${record.forecast_lead_hours}-${idx}`}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    background: idx % 2 === 0 ? "rgba(10, 16, 24, 0.5)" : "transparent",
                  }}
                >
                  <td style={{ padding: "9px 12px", fontWeight: 700, color: "#FFD36A" }}>
                    {record.storm_name}
                  </td>
                  <td style={{ padding: "9px 12px", color: "#A8B2BD" }}>
                    {record.cycle_label || "00Z"}
                  </td>
                  <td style={{ padding: "9px 12px", fontWeight: 600, color: "#FFFFFF" }}>
                    +{String(record.forecast_lead_hours).padStart(2, "0")}h
                  </td>
                  <td style={{ padding: "9px 12px", color: "#8E9DAE", fontFamily: "monospace" }}>
                    {record.forecast_lat?.toFixed(2)}°N, {record.forecast_lon?.toFixed(2)}°E
                  </td>
                  <td style={{ padding: "9px 12px", color: "#45B7D1", fontFamily: "monospace" }}>
                    {record.observed_lat?.toFixed(2)}°N, {record.observed_lon?.toFixed(2)}°E
                  </td>
                  <td style={{ padding: "9px 12px", fontWeight: 700, color: isSevere ? "#EF4444" : "#F59E0B" }}>
                    {record.track_error_km?.toFixed(1)} km
                  </td>
                  <td style={{ padding: "9px 12px", color: "#A8B2BD" }}>
                    {record.threshold_km?.toFixed(1)} km
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <span
                      className="badge"
                      style={{
                        background: isSevere ? "rgba(239, 68, 68, 0.2)" : isDegraded ? "rgba(245, 158, 11, 0.2)" : "rgba(69, 183, 209, 0.2)",
                        color: isSevere ? "#FF7878" : isDegraded ? "#F5B83D" : "#45B7D1",
                        borderColor: isSevere ? "rgba(239, 68, 68, 0.4)" : "rgba(245, 158, 11, 0.4)",
                        fontSize: "10px",
                        padding: "2px 6px",
                      }}
                    >
                      {record.severity}
                    </span>
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <button
                      className="btn-icon"
                      style={{ width: "auto", padding: "3px 8px", fontSize: "10.5px", color: "#F5B83D" }}
                      onClick={() => handleInspect(record.storm_name)}
                    >
                      Inspect Case →
                    </button>
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
