import React from "react";
import { DashboardState } from "../../types/dashboard";
import { STORMS_CATALOG, StormCatalogEntry } from "../../data/casesData";

interface ForecastCasesViewProps {
  state: DashboardState;
  onSelectStorm?: (stormName: string, cycle?: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const ForecastCasesView: React.FC<ForecastCasesViewProps> = ({
  state,
  onSelectStorm,
  onNavigateTab,
}) => {
  const handleLoadCase = (storm: StormCatalogEntry, cycle?: string) => {
    if (onSelectStorm) {
      onSelectStorm(storm.name, cycle || storm.defaultCycle);
    }
    onNavigateTab("dashboard");
  };

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Panel Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            FORECAST CASES BROWSER
          </h2>
          <span className="panel-subtitle">
            13 verified forecast cycles across 6 North Indian Ocean tropical cyclones (101 exact-time verified leads)
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

      {/* Storm Cases Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
        {STORMS_CATALOG.map((storm) => {
          const isCurrentActive = state.activeStormName?.toUpperCase() === storm.name.toUpperCase();
          return (
            <div
              key={storm.stormId}
              className="metric-card"
              style={{
                padding: "16px",
                border: isCurrentActive ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.08)",
                background: isCurrentActive ? "rgba(245, 184, 61, 0.04)" : "rgba(13, 20, 30, 0.6)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                {/* Header row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "15px", fontWeight: 800, color: "#FFFFFF" }}>
                        CYCLONE {storm.name}
                      </span>
                      {isCurrentActive && (
                        <span className="demo-indicator-pill" style={{ fontSize: "9.5px", padding: "1px 6px" }}>
                          ACTIVE CASE
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      {storm.basin} · {storm.dates} ({storm.year})
                    </span>
                  </div>

                  <span
                    className="badge"
                    style={{
                      background: `${storm.tagColor}22`,
                      color: storm.tagColor,
                      borderColor: `${storm.tagColor}55`,
                      fontSize: "10px",
                      fontWeight: 700,
                    }}
                  >
                    {storm.highlightTag}
                  </span>
                </div>

                {/* Narrative */}
                <p style={{ fontSize: "11.5px", color: "#C5D0DC", lineHeight: 1.45, marginBottom: "14px" }}>
                  {storm.narrative}
                </p>

                {/* Metrics row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(10, 16, 24, 0.7)", padding: "10px", borderRadius: "4px", marginBottom: "12px" }}>
                  <div>
                    <div style={{ fontSize: "9px", color: "#8E9DAE", textTransform: "uppercase" }}>Verified Leads</div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>{storm.verifiedLeadsCount}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "9px", color: "#8E9DAE", textTransform: "uppercase" }}>Failures</div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: storm.bustsCount > 0 ? "#EF4444" : "#55D98A" }}>
                      {storm.bustsCount}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "9px", color: "#8E9DAE", textTransform: "uppercase" }}>Peak Error</div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: storm.maxErrorKm > 200 ? "#EF4444" : storm.maxErrorKm > 100 ? "#F59E0B" : "#55D98A" }}>
                      {storm.maxErrorKm.toFixed(1)} km
                    </div>
                  </div>
                </div>

                {/* Available Cycles */}
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ fontSize: "10px", color: "#8E9DAE", marginBottom: "6px", textTransform: "uppercase", fontWeight: 600 }}>
                    Available Cycles ({storm.cycles.length}):
                  </div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {storm.cycles.map((cyc) => (
                      <span
                        key={cyc}
                        style={{
                          background: "rgba(255, 255, 255, 0.05)",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          borderRadius: "3px",
                          padding: "2px 6px",
                          fontSize: "10.5px",
                          fontFamily: "monospace",
                          color: "#FFD36A",
                        }}
                      >
                        {cyc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                className="investigate-btn"
                style={{
                  width: "100%",
                  justifyContent: "center",
                  background: isCurrentActive ? "rgba(245, 184, 61, 0.2)" : "rgba(255, 255, 255, 0.08)",
                  border: isCurrentActive ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.15)",
                  color: isCurrentActive ? "#F5B83D" : "#FFFFFF",
                  fontSize: "11.5px",
                }}
                onClick={() => handleLoadCase(storm)}
              >
                <span>{isCurrentActive ? "Active in Workspace" : "Load Case into Workspace →"}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
