import React, { useState } from "react";
import { DashboardState } from "../../types/dashboard";
import { BUST_ATLAS_DATA, STORMS_CATALOG } from "../../data/casesData";

interface BustAtlasViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
  onSelectStorm?: (stormName: string) => void;
  onSelectLead?: (lead: string) => void;
}

export const BustAtlasView: React.FC<BustAtlasViewProps> = ({
  state: _state,
  onNavigateTab,
  onSelectStorm,
  onSelectLead,
}) => {
  const [filterStorm, setFilterStorm] = useState<string>("ALL");
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filtered = BUST_ATLAS_DATA.filter((r: any) => {
    if (filterStorm !== "ALL" && r.storm_name.toUpperCase() !== filterStorm.toUpperCase()) return false;
    if (filterSeverity !== "ALL" && r.severity !== filterSeverity) return false;
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      return (
        r.storm_name.toLowerCase().includes(q) ||
        r.cycle_label?.toLowerCase().includes(q) ||
        String(r.forecast_lead_hours).includes(q)
      );
    }
    return true;
  });

  const handleOpenInvestigation = (stormName: string, leadHours: number) => {
    if (onSelectStorm) {
      onSelectStorm(stormName);
    }
    if (onSelectLead) {
      onSelectLead(`+${String(leadHours).padStart(2, "0")}h`);
    }
    onNavigateTab("forecast_vs_reality");
  };

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
            BUST ATLAS — CURATED FAILURE REGISTRY (24 VERIFIED CASES)
          </h2>
          <span className="panel-subtitle">
            Comprehensive catalog of verified forecast track failures in North Indian Ocean tropical cyclones
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

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", background: "rgba(10, 16, 24, 0.8)", padding: "10px 14px", borderRadius: "6px" }}>
        <input
          type="text"
          placeholder="Search by storm, cycle, or lead..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="select-control"
          style={{ padding: "5px 10px", fontSize: "11px", minWidth: "220px" }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "#A8B2BD" }}>Storm:</span>
          <select
            value={filterStorm}
            onChange={(e) => setFilterStorm(e.target.value)}
            className="select-control"
            style={{ padding: "4px 8px", fontSize: "11px" }}
          >
            <option value="ALL">All Storms</option>
            {STORMS_CATALOG.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "#A8B2BD" }}>Severity:</span>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="select-control"
            style={{ padding: "4px 8px", fontSize: "11px" }}
          >
            <option value="ALL">All Severities</option>
            <option value="SEVERE">Severe</option>
            <option value="DEGRADED">Degraded</option>
            <option value="MODERATE">Moderate</option>
          </select>
        </div>

        <span style={{ fontSize: "11px", color: "#8E9DAE", marginLeft: "auto" }}>
          {filtered.length} of {BUST_ATLAS_DATA.length} failure records
        </span>
      </div>

      {/* Atlas Table */}
      <div style={{ overflowX: "auto", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "6px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
              <th style={{ padding: "10px 12px" }}>STORM</th>
              <th style={{ padding: "10px 12px" }}>CYCLE</th>
              <th style={{ padding: "10px 12px" }}>LEAD</th>
              <th style={{ padding: "10px 12px" }}>TRACK ERROR</th>
              <th style={{ padding: "10px 12px" }}>TOLERANCE &tau;</th>
              <th style={{ padding: "10px 12px" }}>EXCESS (km)</th>
              <th style={{ padding: "10px 12px" }}>SEVERITY</th>
              <th style={{ padding: "10px 12px" }}>INVESTIGATE</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r: any, idx: number) => {
              const excess = Math.max(0, (r.track_error_km || 0) - (r.threshold_km || 0));
              const isSevere = r.severity === "SEVERE";
              return (
                <tr
                  key={`${r.storm_name}-${r.forecast_lead_hours}-${idx}`}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    background: idx % 2 === 0 ? "rgba(10, 16, 24, 0.5)" : "transparent",
                  }}
                >
                  <td style={{ padding: "9px 12px", fontWeight: 700, color: "#FFD36A" }}>{r.storm_name}</td>
                  <td style={{ padding: "9px 12px", color: "#A8B2BD" }}>{r.cycle_label || "00Z"}</td>
                  <td style={{ padding: "9px 12px", fontWeight: 600, color: "#FFFFFF" }}>
                    +{String(r.forecast_lead_hours).padStart(2, "0")}h
                  </td>
                  <td style={{ padding: "9px 12px", fontWeight: 700, color: isSevere ? "#EF4444" : "#F59E0B" }}>
                    {r.track_error_km?.toFixed(1)} km
                  </td>
                  <td style={{ padding: "9px 12px", color: "#A8B2BD" }}>{r.threshold_km?.toFixed(1)} km</td>
                  <td style={{ padding: "9px 12px", color: "#FF7878" }}>+{excess.toFixed(1)} km</td>
                  <td style={{ padding: "9px 12px" }}>
                    <span
                      className="badge"
                      style={{
                        background: isSevere ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                        color: isSevere ? "#FF7878" : "#F5B83D",
                        borderColor: isSevere ? "rgba(239, 68, 68, 0.4)" : "rgba(245, 158, 11, 0.4)",
                        fontSize: "9.5px",
                        padding: "2px 6px",
                      }}
                    >
                      {r.severity}
                    </span>
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <button
                      className="btn-icon"
                      style={{ width: "auto", padding: "3px 8px", fontSize: "10.5px", color: "#45B7D1" }}
                      onClick={() => handleOpenInvestigation(r.storm_name, r.forecast_lead_hours)}
                    >
                      Open Case →
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
